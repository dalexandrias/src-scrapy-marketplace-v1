"""
Engine de scraping adaptado para monitoramento do Facebook Marketplace
Usa a URL da API do Facebook para buscar anúncios mais recentes
"""

import time
import re
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

from .db_manager import DatabaseManager
from utils.logger import get_logger

class ScraperEngine:
    def __init__(self, db_manager: DatabaseManager, logger=None):
        self.db = db_manager
        self.logger = logger or get_logger("ScraperEngine", db_manager)
        self.driver = None
        
        # Configurações do scraper
        self.config = {
            'headless': self.db.get_config('headless_browser', True),  # Sempre headless por padrão para evitar problemas
            'timeout': self.db.get_config('timeout_request', 30),
            'max_retries': self.db.get_config('max_retries', 3),
            'max_listings': self.db.get_config('max_listings_per_check', 50),
            'show_browser_logs': self.db.get_config('show_browser_logs', False)  # Não mostrar logs do Chrome por padrão
        }
    
    def setup_driver(self) -> webdriver.Chrome:
        """Configurar driver do Chrome otimizado"""
        chrome_options = Options()
        
        if self.config['headless']:
            chrome_options.add_argument("--headless")
        
        # Configurações para performance e stealth
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")
        
        # Suprimir logs se configurado
        if not self.config['show_browser_logs']:
            chrome_options.add_argument("--disable-logging")
            chrome_options.add_argument("--log-level=3")
            chrome_options.add_argument("--silent")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
            chrome_options.add_experimental_option("useAutomationExtension", False)
        chrome_options.add_argument("--silent")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # Anti-detecção
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # User agent realista
        chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        
        try:
            # Configurar argumentos do service
            service_args = []
            if not self.config['show_browser_logs']:
                service_args.append('--silent')
            
            service = Service(
                ChromeDriverManager().install(),
                log_path='NUL' if not self.config['show_browser_logs'] else None,
                service_args=service_args
            )
            
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Configurações anti-detecção
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": chrome_options.arguments[-1].split('=', 1)[1]
            })
            
            # Configurar timeouts
            driver.set_page_load_timeout(self.config['timeout'])
            driver.set_script_timeout(self.config['timeout'])
            
            return driver
            
        except Exception as e:
            self.logger.error(f"Erro ao configurar driver Chrome: {e}")
            raise
            driver.implicitly_wait(10)
            
            return driver
            
        except Exception as e:
            self.logger.error(f"Erro ao configurar driver: {e}")
            raise
    
    def build_marketplace_url(self, city_slug: str, keyword: str = None, 
                             category: str = "vehicles") -> str:
        """Construir URL do Facebook Marketplace"""
        base_url = f"https://www.facebook.com/marketplace/{city_slug}"
        
        # Se há palavra-chave, usar /search/, senão usar categoria específica
        if keyword:
            base_url += "/search"
        elif category:
            base_url += f"/{category}"
        
        # Parâmetros para buscar mais recentes
        params = [
            "sortBy=creation_time_descend",  # Ordenar por mais recentes
            "exact=false"
        ]
        
        if keyword:
            # Codificar keyword para URL
            import urllib.parse
            encoded_keyword = urllib.parse.quote(keyword)
            params.insert(0, f"query={encoded_keyword}")
        
        if params:
            base_url += "?" + "&".join(params)
        
        return base_url
    
    def extract_facebook_id_from_url(self, url: str) -> Optional[str]:
        """Extrair ID do Facebook da URL do anúncio"""
        # Padrão: /marketplace/item/1234567890/
        match = re.search(r'/marketplace/item/(\d+)/', url)
        if match:
            return match.group(1)
        return None
    
    def extract_listing_data(self, listing_element) -> Optional[Dict[str, Any]]:
        """Extrair dados de um elemento de anúncio"""
        try:
            # Scroll para o elemento
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", listing_element)
            time.sleep(0.3)
            
            data = {}
            
            # URL e ID do Facebook
            try:
                if listing_element.tag_name == 'a':
                    url = listing_element.get_attribute('href')
                else:
                    link_elem = listing_element.find_element(By.CSS_SELECTOR, "a")
                    url = link_elem.get_attribute('href')
                
                data['url'] = url
                data['facebook_id'] = self.extract_facebook_id_from_url(url)
                
                if not data['facebook_id']:
                    return None
                    
            except Exception:
                return None
            
            # Título
            title_selectors = [
                'span[dir="auto"]',
                'div[role="button"] span',
                'h3 span',
                'span'
            ]
            
            data['title'] = None
            for selector in title_selectors:
                try:
                    elements = listing_element.find_elements(By.CSS_SELECTOR, selector)
                    for elem in elements:
                        text = elem.text.strip()
                        # Verificar se é um título válido (não é só preço ou localização)
                        if (text and len(text) > 5 and 
                            not re.match(r'^(US\$|R\$|€|\$)\d+', text) and
                            not re.match(r'^\d+\s*(km|mi|miles)', text.lower())):
                            data['title'] = text[:200]  # Limitar tamanho
                            break
                    if data['title']:
                        break
                except Exception:
                    continue
            
            # Preço
            price_selectors = [
                'span:contains("$")',
                'span:contains("R$")',
                'div:contains("$")'
            ]
            
            data['price'] = None
            try:
                # Buscar por elementos que contêm símbolos de moeda
                all_spans = listing_element.find_elements(By.CSS_SELECTOR, "span, div")
                for span in all_spans:
                    text = span.text.strip()
                    if re.search(r'(US\$|R\$|€|\$)\s*[\d,]+', text):
                        data['price'] = text[:50]  # Limitar tamanho
                        break
            except Exception:
                pass
            
            # Localização (tentar extrair de textos menores)
            data['location'] = None
            try:
                all_elements = listing_element.find_elements(By.CSS_SELECTOR, "span, div")
                for elem in all_elements:
                    text = elem.text.strip()
                    # Procurar por padrões de localização brasileira
                    if (text and len(text) < 100 and 
                        re.search(r'\b(SP|RJ|MG|São Paulo|Rio|Santo André|ABC|km)\b', text, re.IGNORECASE)):
                        data['location'] = text
                        break
            except Exception:
                pass
            
            # Imagem
            data['image_url'] = None
            try:
                img_elem = listing_element.find_element(By.CSS_SELECTOR, "img")
                src = img_elem.get_attribute('src')
                if src and src.startswith('http'):
                    data['image_url'] = src
            except Exception:
                pass
            
            # Validar dados mínimos
            if not data.get('facebook_id') or not data.get('url'):
                return None
            
            # Se não tem título, criar um baseado no preço ou ID
            if not data.get('title'):
                if data.get('price'):
                    data['title'] = f"Anúncio - {data['price']}"
                else:
                    data['title'] = f"Anúncio #{data['facebook_id']}"
            
            return data
            
        except Exception as e:
            self.logger.debug(f"Erro ao extrair dados do anúncio: {e}")
            return None
    
    def scrape_marketplace(self, city_slug: str, keyword: str, city_id: int, 
                          keyword_id: int) -> Dict[str, Any]:
        """Fazer scraping do marketplace para uma combinação cidade/keyword"""
        start_time = time.time()
        result = {
            'success': False,
            'listings_found': 0,
            'new_listings': 0,
            'errors': 0,
            'error_message': None,
            'execution_time_ms': 0
        }
        
        try:
            # Configurar driver se necessário
            if not self.driver:
                self.driver = self.setup_driver()
            
            # Construir URL
            url = self.build_marketplace_url(city_slug, keyword, "vehicles")
            self.logger.info(f"Acessando: {url}")
            
            # Navegar para a página
            self.driver.get(url)
            time.sleep(3)
            
            # Verificar se foi redirecionado para login
            if "login" in self.driver.current_url.lower():
                raise Exception("Redirecionado para login do Facebook")
            
            # Aguardar carregamento da página
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'a[href*="/marketplace/item/"]'))
                )
            except TimeoutException:
                self.logger.warning("Timeout aguardando anúncios")
            
            # Scroll para carregar mais anúncios
            self.scroll_and_load()
            
            # Encontrar todos os anúncios
            listings = self.driver.find_elements(By.CSS_SELECTOR, 'a[href*="/marketplace/item/"]')
            result['listings_found'] = len(listings)
            
            if not listings:
                self.logger.warning(f"Nenhum anúncio encontrado para '{keyword}' em {city_slug}")
                result['success'] = True
                return result
            
            self.logger.info(f"Encontrados {len(listings)} anúncios")
            
            # Processar anúncios limitados
            max_to_process = min(len(listings), self.config['max_listings'])
            new_listings = 0
            
            for i, listing in enumerate(listings[:max_to_process]):
                try:
                    data = self.extract_listing_data(listing)
                    
                    if data and data.get('facebook_id'):
                        # Verificar se já existe no banco
                        if not self.db.listing_exists(data['facebook_id']):
                            # Adicionar novo anúncio
                            listing_id = self.db.add_listing(
                                facebook_id=data['facebook_id'],
                                title=data.get('title', ''),
                                price=data.get('price', ''),
                                url=data['url'],
                                description=None,  # Pode ser expandido depois
                                location=data.get('location', ''),
                                image_url=data.get('image_url', ''),
                                city_id=city_id,
                                keyword_id=keyword_id
                            )
                            
                            new_listings += 1
                            self.logger.info(f"Novo anúncio: {data['title'][:50]}...")
                            
                        # Delay entre processamentos
                        time.sleep(0.5)
                        
                except Exception as e:
                    result['errors'] += 1
                    self.logger.debug(f"Erro ao processar anúncio {i+1}: {e}")
                    continue
            
            result['new_listings'] = new_listings
            result['success'] = True
            
            self.logger.info(f"Concluído: {new_listings} novos de {result['listings_found']} anúncios")
            
        except Exception as e:
            result['error_message'] = str(e)
            result['errors'] += 1
            self.logger.error(f"Erro no scraping: {e}")
        
        finally:
            # Calcular tempo de execução
            result['execution_time_ms'] = int((time.time() - start_time) * 1000)
            
            # Salvar estatísticas
            self.db.add_execution_stat(
                keyword_id=keyword_id,
                city_id=city_id,
                execution_time_ms=result['execution_time_ms'],
                listings_found=result['listings_found'],
                new_listings=result['new_listings'],
                errors=result['errors']
            )
        
        return result
    
    def scroll_and_load(self, max_scrolls: int = 3):
        """Fazer scroll para carregar mais anúncios"""
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        
        for i in range(max_scrolls):
            # Scroll para baixo
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # Verificar se carregou mais conteúdo
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            
            if new_height == last_height:
                break
            
            last_height = new_height
            self.logger.debug(f"Scroll {i+1}/{max_scrolls} completado")
    
    def close_driver(self):
        """Fechar driver do navegador"""
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
                self.logger.debug("Driver fechado")
            except Exception as e:
                self.logger.warning(f"Erro ao fechar driver: {e}")
    
    def __del__(self):
        """Destructor para garantir que o driver seja fechado"""
        self.close_driver()
    
    def check_keyword_city_combination(self, keyword: Dict[str, Any], city: Dict[str, Any]) -> Dict[str, Any]:
        """Método para testar uma combinação específica de palavra-chave e cidade"""
        return self.scrape_marketplace(keyword['id'], keyword['term'], city['id'], city['facebook_slug'])
