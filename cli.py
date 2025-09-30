"""
Interface de linha de comando para o sistema de monitoramento
Permite configurar e controlar o sistema via CLI
"""

import argparse
import sys
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any

from core.db_manager import DatabaseManager
from core.monitor_service import MonitorService
from utils.logger import get_logger

class CLI:
    """Interface de linha de comando"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.logger = get_logger("CLI", self.db)
        self.monitor = MonitorService()
    
    def cmd_init(self, args):
        """Inicializar o sistema"""
        print("🚀 Inicializando sistema de monitoramento...")
        
        try:
            # Verificar se banco já existe
            info = self.db.get_database_info()
            
            print(f"✅ Banco de dados inicializado")
            print(f"   📁 Localização: {self.db.db_path}")
            print(f"   📊 Cidades: {info['cities_count']}")
            print(f"   🔍 Palavras-chave: {info['keywords_count']}")
            print(f"   📝 Anúncios: {info['listings_count']}")
            
            # Mostrar cidades padrão
            cities = self.db.get_cities()
            print(f"\n🏙️  Cidades configuradas ({len(cities)}):")
            for city in cities[:5]:
                status = "✅" if city['active'] else "❌"
                print(f"   {status} {city['name']} ({city['facebook_slug']})")
            
            if len(cities) > 5:
                print(f"   ... e mais {len(cities) - 5} cidades")
            
            # Mostrar palavras-chave padrão
            keywords = self.db.get_keywords()
            print(f"\n🔍 Palavras-chave configuradas ({len(keywords)}):")
            for kw in keywords[:5]:
                status = "✅" if kw['active'] else "❌"
                print(f"   {status} {kw['term']} (intervalo: {kw['check_interval']}s)")
            
            if len(keywords) > 5:
                print(f"   ... e mais {len(keywords) - 5} palavras-chave")
            
            print(f"\n💡 Use 'python main.py --help' para ver todos os comandos")
            
        except Exception as e:
            print(f"❌ Erro na inicialização: {e}")
            return 1
        
        return 0
    
    def cmd_city_add(self, args):
        """Adicionar nova cidade"""
        try:
            city_id = self.db.add_city(args.name, args.slug, args.active)
            print(f"✅ Cidade '{args.name}' adicionada (ID: {city_id})")
            return 0
        except Exception as e:
            print(f"❌ Erro ao adicionar cidade: {e}")
            return 1
    
    def cmd_city_list(self, args):
        """Listar cidades"""
        cities = self.db.get_cities(active_only=not args.all)
        
        if not cities:
            print("📭 Nenhuma cidade encontrada")
            return 0
        
        print(f"🏙️  Cidades {'ativas' if not args.all else 'cadastradas'} ({len(cities)}):")
        print(f"{'ID':<4} {'Status':<8} {'Nome':<25} {'Slug Facebook':<20}")
        print("-" * 65)
        
        for city in cities:
            status = "✅ Ativa" if city['active'] else "❌ Inativa"
            print(f"{city['id']:<4} {status:<8} {city['name']:<25} {city['facebook_slug']:<20}")
        
        return 0
    
    def cmd_city_toggle(self, args):
        """Ativar/desativar cidade"""
        try:
            # Buscar cidade
            cities = self.db.get_cities(active_only=False)
            city = next((c for c in cities if c['facebook_slug'] == args.slug), None)
            
            if not city:
                print(f"❌ Cidade '{args.slug}' não encontrada")
                return 1
            
            new_status = not city['active']
            self.db.update_city_status(city['id'], new_status)
            
            status_text = "ativada" if new_status else "desativada"
            print(f"✅ Cidade '{city['name']}' {status_text}")
            return 0
            
        except Exception as e:
            print(f"❌ Erro ao atualizar cidade: {e}")
            return 1
    
    def cmd_keyword_add(self, args):
        """Adicionar nova palavra-chave"""
        try:
            keyword_id = self.db.add_keyword(args.term, args.interval, args.active)
            print(f"✅ Palavra-chave '{args.term}' adicionada (ID: {keyword_id})")
            print(f"   ⏱️  Intervalo: {args.interval} segundos")
            return 0
        except Exception as e:
            print(f"❌ Erro ao adicionar palavra-chave: {e}")
            return 1
    
    def cmd_keyword_list(self, args):
        """Listar palavras-chave"""
        keywords = self.db.get_keywords(active_only=not args.all)
        
        if not keywords:
            print("📭 Nenhuma palavra-chave encontrada")
            return 0
        
        print(f"🔍 Palavras-chave {'ativas' if not args.all else 'cadastradas'} ({len(keywords)}):")
        print(f"{'ID':<4} {'Status':<8} {'Termo':<20} {'Intervalo':<10} {'Verificações':<12} {'Encontrados':<12}")
        print("-" * 75)
        
        for kw in keywords:
            status = "✅ Ativa" if kw['active'] else "❌ Inativa"
            last_check = "Nunca" if not kw['last_check'] else kw['last_check'][:16]
            
            print(f"{kw['id']:<4} {status:<8} {kw['term']:<20} {kw['check_interval']:<10} "
                  f"{kw['total_checks']:<12} {kw['total_found']:<12}")
        
        return 0
    
    def cmd_keyword_update(self, args):
        """Atualizar palavra-chave"""
        try:
            if args.interval:
                self.db.update_keyword_interval(args.keyword_id, args.interval)
                print(f"✅ Intervalo da palavra-chave ID {args.keyword_id} atualizado para {args.interval}s")
            
            return 0
        except Exception as e:
            print(f"❌ Erro ao atualizar palavra-chave: {e}")
            return 1
    
    def cmd_start(self, args):
        """Iniciar monitoramento"""
        print("🚀 Iniciando monitoramento do Facebook Marketplace...")
        
        try:
            # Verificar configurações
            keywords = self.db.get_keywords(active_only=True)
            cities = self.db.get_cities(active_only=True)
            
            if not keywords:
                print("❌ Nenhuma palavra-chave ativa encontrada. Use 'keyword add' para adicionar.")
                return 1
            
            if not cities:
                print("❌ Nenhuma cidade ativa encontrada. Use 'city add' para adicionar.")
                return 1
            
            print(f"📊 Configuração atual:")
            print(f"   🔍 {len(keywords)} palavras-chave ativas")
            print(f"   🏙️  {len(cities)} cidades ativas")
            print(f"   📱 Notificações: {'habilitadas' if self.db.get_config('notification_enabled') else 'desabilitadas'}")
            
            # Configurar modo visual se solicitado
            if args.visual:
                self.db.set_config('headless_browser', False)
                print("👁️  Modo visual ativado - navegador será visível")
            
            if args.show_logs:
                self.db.set_config('show_browser_logs', True)
                print("📋 Modo debug ativado - logs do navegador serão exibidos")
            
            if args.daemon:
                print("🔄 Executando em modo daemon...")
            else:
                print("⚠️  Pressione Ctrl+C para parar")
            
            print("-" * 50)
            
            # Iniciar monitoramento
            self.monitor.start()
            
            return 0
            
        except KeyboardInterrupt:
            print("\n⚠️  Monitoramento interrompido pelo usuário")
            return 0
        except Exception as e:
            print(f"❌ Erro ao iniciar monitoramento: {e}")
            return 1
    
    def cmd_status(self, args):
        """Mostrar status do sistema"""
        try:
            status = self.monitor.get_status()
            
            # Cabeçalho
            print("📊 STATUS DO SISTEMA")
            print("=" * 50)
            
            # Status básico
            running_status = "🟢 Executando" if status['running'] else "🔴 Parado"
            print(f"Status: {running_status}")
            print(f"Uptime: {status['uptime']}")
            
            # Estatísticas 24h
            stats = status['stats_24h']
            print(f"\n📈 Estatísticas (24h):")
            print(f"   Execuções: {stats.get('total_executions', 0)}")
            print(f"   Anúncios encontrados: {stats.get('total_listings_found', 0) or 0}")
            print(f"   Anúncios novos: {stats.get('total_new_listings', 0) or 0}")
            print(f"   Tempo médio: {stats.get('avg_execution_time', 0) or 0:.0f}ms")
            print(f"   Erros: {stats.get('total_errors', 0) or 0}")
            
            # Top keywords
            if stats.get('top_keywords'):
                print(f"\n🔝 Top palavras-chave:")
                for kw in stats['top_keywords'][:3]:
                    print(f"   {kw['term']}: {kw['new_listings']} novos")
            
            # Próximas verificações
            if status['next_checks']:
                print(f"\n⏰ Próximas verificações:")
                for check in status['next_checks']:
                    print(f"   {check['next_check']} - {check['keyword']} ({check['interval']}s)")
            
            # Info do banco
            db_info = status['database_info']
            print(f"\n💾 Banco de dados:")
            print(f"   Tamanho: {db_info['file_size_mb']} MB")
            print(f"   Anúncios: {db_info['listings_count']}")
            print(f"   Logs: {db_info['system_logs_count']}")
            
            return 0
            
        except Exception as e:
            print(f"❌ Erro ao obter status: {e}")
            return 1
    
    def cmd_report(self, args):
        """Gerar relatório"""
        try:
            hours = args.hours
            print(f"📋 RELATÓRIO - Últimas {hours} horas")
            print("=" * 50)
            
            # Anúncios recentes
            recent_listings = self.db.get_recent_listings(hours, limit=50)
            
            if recent_listings:
                print(f"🆕 Anúncios encontrados: {len(recent_listings)}")
                print("\nÚltimos 10 anúncios:")
                
                for i, listing in enumerate(recent_listings[:10]):
                    found_time = listing['found_at'][:16]  # YYYY-MM-DD HH:MM
                    title = listing['title'][:40] + "..." if len(listing['title']) > 40 else listing['title']
                    price = listing['price'] or 'Sem preço'
                    keyword = listing['keyword_term'] or 'N/A'
                    
                    print(f"   {i+1:2d}. [{found_time}] {title}")
                    print(f"       💰 {price} | 🔍 {keyword}")
            else:
                print("📭 Nenhum anúncio encontrado no período")
            
            # Estatísticas
            stats = self.db.get_stats_summary(hours)
            print(f"\n📊 Resumo estatístico:")
            print(f"   Execuções: {stats.get('total_executions', 0)}")
            print(f"   Novos anúncios: {stats.get('total_new_listings', 0)}")
            print(f"   Tempo médio: {stats.get('avg_execution_time', 0):.0f}ms")
            
            return 0
            
        except Exception as e:
            print(f"❌ Erro ao gerar relatório: {e}")
            return 1
    
    def cmd_config(self, args):
        """Gerenciar configurações"""
        try:
            if args.list:
                # Listar configurações
                config = self.db.get_all_config()
                print("⚙️  Configurações do sistema:")
                print("-" * 40)
                
                for key, value in config.items():
                    print(f"{key:<25}: {value}")
                
            elif args.set:
                # Definir configuração
                key, value = args.set
                self.db.set_config(key, value)
                print(f"✅ Configuração '{key}' definida como '{value}'")
            
            elif args.get:
                # Obter configuração
                value = self.db.get_config(args.get)
                print(f"{args.get}: {value}")
            
            return 0
            
        except Exception as e:
            print(f"❌ Erro na configuração: {e}")
            return 1
    
    def cmd_test(self, args):
        """Testar uma busca específica"""
        try:
            print(f"🧪 Testando busca: '{args.keyword}' em {args.city}")
            
            # Buscar cidade
            city = self.db.get_city_by_slug(args.city)
            if not city:
                print(f"❌ Cidade '{args.city}' não encontrada")
                return 1
            
            # Buscar ou criar palavra-chave temporária
            keywords = self.db.get_keywords(active_only=False)
            keyword = next((k for k in keywords if k['term'] == args.keyword), None)
            
            if not keyword:
                print(f"⚠️  Palavra-chave '{args.keyword}' não encontrada, criando temporariamente...")
                keyword_id = self.db.add_keyword(args.keyword, 120, False)
                keyword = {'id': keyword_id, 'term': args.keyword}
            
            # Executar teste
            print("🔍 Executando busca...")
            
            from core.scraper_engine import ScraperEngine
            scraper = ScraperEngine(self.db, self.logger)
            
            result = scraper.check_keyword_city_combination(keyword, city)
            
            # Mostrar resultados
            print(f"\n📊 Resultados:")
            print(f"   Status: {'✅ Sucesso' if result['success'] else '❌ Erro'}")
            print(f"   Anúncios encontrados: {result['listings_found']}")
            print(f"   Anúncios novos: {result['new_listings']}")
            print(f"   Tempo de execução: {result['execution_time_ms']}ms")
            
            if result.get('error_message'):
                print(f"   Erro: {result['error_message']}")
            
            # Limpar driver
            scraper.close_driver()
            
            return 0 if result['success'] else 1
            
        except Exception as e:
            print(f"❌ Erro no teste: {e}")
            return 1

def create_parser():
    """Criar parser de argumentos"""
    parser = argparse.ArgumentParser(
        description='Sistema de Monitoramento do Facebook Marketplace',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  python main.py init                           # Inicializar sistema
  python main.py city add "São Paulo" saopaulo # Adicionar cidade
  python main.py keyword add "honda civic"      # Adicionar palavra-chave
  python main.py start                          # Iniciar monitoramento
  python main.py status                         # Ver status
  python main.py report --hours 24             # Relatório 24h
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Comandos disponíveis')
    
    # Comando init
    subparsers.add_parser('init', help='Inicializar o sistema')
    
    # Comandos de cidade
    city_parser = subparsers.add_parser('city', help='Gerenciar cidades')
    city_subparsers = city_parser.add_subparsers(dest='city_action')
    
    city_add = city_subparsers.add_parser('add', help='Adicionar cidade')
    city_add.add_argument('name', help='Nome da cidade')
    city_add.add_argument('slug', help='Slug do Facebook')
    city_add.add_argument('--active', action='store_true', default=True, help='Cidade ativa')
    
    city_list = city_subparsers.add_parser('list', help='Listar cidades')
    city_list.add_argument('--all', action='store_true', help='Incluir inativas')
    
    city_toggle = city_subparsers.add_parser('toggle', help='Ativar/desativar cidade')
    city_toggle.add_argument('slug', help='Slug da cidade')
    
    # Comandos de palavra-chave
    kw_parser = subparsers.add_parser('keyword', help='Gerenciar palavras-chave')
    kw_subparsers = kw_parser.add_subparsers(dest='keyword_action')
    
    kw_add = kw_subparsers.add_parser('add', help='Adicionar palavra-chave')
    kw_add.add_argument('term', help='Termo de busca')
    kw_add.add_argument('--interval', type=int, default=120, help='Intervalo em segundos')
    kw_add.add_argument('--active', action='store_true', default=True, help='Palavra-chave ativa')
    
    kw_list = kw_subparsers.add_parser('list', help='Listar palavras-chave')
    kw_list.add_argument('--all', action='store_true', help='Incluir inativas')
    
    kw_update = kw_subparsers.add_parser('update', help='Atualizar palavra-chave')
    kw_update.add_argument('keyword_id', type=int, help='ID da palavra-chave')
    kw_update.add_argument('--interval', type=int, help='Novo intervalo')
    
    # Comando start
    start_parser = subparsers.add_parser('start', help='Iniciar monitoramento')
    start_parser.add_argument('--daemon', action='store_true', help='Executar em background')
    start_parser.add_argument('--visual', action='store_true', help='Executar com navegador visível (para debug)')
    start_parser.add_argument('--show-logs', action='store_true', help='Mostrar logs do navegador')
    
    # Comando status
    subparsers.add_parser('status', help='Mostrar status do sistema')
    
    # Comando report
    report_parser = subparsers.add_parser('report', help='Gerar relatório')
    report_parser.add_argument('--hours', type=int, default=24, help='Período em horas')
    
    # Comando config
    config_parser = subparsers.add_parser('config', help='Gerenciar configurações')
    config_group = config_parser.add_mutually_exclusive_group(required=True)
    config_group.add_argument('--list', action='store_true', help='Listar configurações')
    config_group.add_argument('--set', nargs=2, metavar=('KEY', 'VALUE'), help='Definir configuração')
    config_group.add_argument('--get', help='Obter configuração')
    
    # Comando test
    test_parser = subparsers.add_parser('test', help='Testar busca específica')
    test_parser.add_argument('keyword', help='Palavra-chave para testar')
    test_parser.add_argument('city', help='Slug da cidade')
    
    return parser

def main():
    """Função principal"""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    cli = CLI()
    
    # Mapear comandos para métodos
    command_map = {
        'init': cli.cmd_init,
        'start': cli.cmd_start,
        'status': cli.cmd_status,
        'report': cli.cmd_report,
        'config': cli.cmd_config,
        'test': cli.cmd_test
    }
    
    # Comandos compostos
    if args.command == 'city':
        if args.city_action == 'add':
            return cli.cmd_city_add(args)
        elif args.city_action == 'list':
            return cli.cmd_city_list(args)
        elif args.city_action == 'toggle':
            return cli.cmd_city_toggle(args)
    
    elif args.command == 'keyword':
        if args.keyword_action == 'add':
            return cli.cmd_keyword_add(args)
        elif args.keyword_action == 'list':
            return cli.cmd_keyword_list(args)
        elif args.keyword_action == 'update':
            return cli.cmd_keyword_update(args)
    
    # Comandos simples
    elif args.command in command_map:
        return command_map[args.command](args)
    
    else:
        print(f"❌ Comando '{args.command}' não implementado")
        return 1

if __name__ == '__main__':
    sys.exit(main())
