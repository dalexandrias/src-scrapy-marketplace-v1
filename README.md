# 🚗 Sistema de Monitoramento do Facebook Marketplace

Sistema #### 4. Iniciar Monitoramento
```bash
# Executar interativamente (recomendado)
python main.py start

# Executar em background (daemon)
python main.py start --daemon

# Executar com navegador visível (para debug)
python main.py start --visual

# Executar com logs do navegador (para troubleshooting)
python main.py start --show-logs
```zado para monitorar anúncios de veículos no Facebook Marketplace, com notificações em tempo real e persistência de dados.

## ✨ Funcionalidades

- **Monitoramento Automatizado**: Verifica anúncios em intervalos configuráveis
- **Múltiplas Cidades**: Monitora várias cidades simultaneamente
- **Palavras-chave Personalizadas**: Configure termos específicos de busca
- **Banco SQLite**: Armazena anúncios, logs e configurações
- **Notificações**: Console e arquivo para novos anúncios
- **Interface CLI**: Controle completo via linha de comando
- **Estatísticas**: Relatórios detalhados de performance

## 🛠️ Instalação

### Dependências Python
```bash
pip install -r requirements.txt
```

Ou instalar manualmente:
```bash
pip install selenium webdriver-manager requests beautifulsoup4 colorama
```

## 🚀 Configuração Inicial

### 1. Inicializar o Sistema
```bash
python main.py init
```

Este comando:
- Cria o banco de dados SQLite
- Configura tabelas e índices
- Adiciona cidades e palavras-chave padrão
- Mostra o status inicial

### 2. Configurar Cidades
```bash
# Adicionar nova cidade
python main.py city add "São Paulo" sao-paulo

# Listar cidades
python main.py city list

# Ativar/desativar cidade
python main.py city toggle sao-paulo
```

### 3. Configurar Palavras-chave
```bash
# Adicionar palavra-chave
python main.py keyword add "honda civic" --interval 120

# Listar palavras-chave
python main.py keyword list

# Atualizar intervalo
python main.py keyword update 1 --interval 300
```

## 🎯 Uso Básico

### Iniciar Monitoramento
```bash
# Executar interativamente
python main.py start

# Executar em background (daemon)
python main.py start --daemon
```

### Verificar Status
```bash
python main.py status
```

Mostra:
- Status do serviço (executando/parado)
- Estatísticas das últimas 24h
- Próximas verificações agendadas
- Informações do banco de dados

### Gerar Relatórios
```bash
# Relatório das últimas 24 horas
python main.py report

# Relatório das últimas 6 horas
python main.py report --hours 6
```

### Testar Configuração
```bash
# Testar busca específica
python main.py test "honda civic" sao-paulo
```

## ⚙️ Configurações Avançadas

### Gerenciar Configurações
```bash
# Listar todas as configurações
python main.py config --list

# Definir configuração
python main.py config --set notification_enabled true

# Obter configuração específica
python main.py config --get max_browser_instances
```

### Configurações Disponíveis
- `notification_enabled`: Habilitar notificações (true/false)
- `max_browser_instances`: Máximo de navegadores simultâneos (padrão: 3)
- `request_delay_ms`: Delay entre requisições em ms (padrão: 2000)
- `cleanup_older_than_days`: Limpar logs mais antigos que X dias (padrão: 30)
- `max_listings_per_keyword`: Máximo de anúncios por busca (padrão: 100)

## 📁 Estrutura do Projeto

```
marketplace_monitor/
├── main.py                 # Ponto de entrada
├── cli.py                  # Interface de linha de comando
├── config/
│   └── database.sql        # Schema do banco de dados
├── core/
│   ├── db_manager.py       # Gerenciador do banco de dados
│   ├── scraper_engine.py   # Motor de scraping
│   └── monitor_service.py  # Serviço principal de monitoramento
├── notifications/
│   ├── base.py            # Classe base para notificações
│   ├── console.py         # Notificações no console
│   └── file.py            # Notificações em arquivo
└── utils/
    └── logger.py          # Sistema de logging
```

## 🗄️ Banco de Dados

O sistema usa SQLite com as seguintes tabelas:

- **cities**: Cidades monitoradas
- **keywords**: Palavras-chave de busca
- **listings**: Anúncios encontrados
- **system_logs**: Logs do sistema
- **notifications**: Histórico de notificações
- **execution_stats**: Estatísticas de execução
- **config**: Configurações do sistema

## 🔧 Customização

### Adicionar Novo Tipo de Notificação

1. Crie uma classe em `notifications/` herdando de `BaseNotifier`
2. Implemente o método `send()`
3. Registre no `monitor_service.py`

### Modificar Lógica de Scraping

1. Edite `scraper_engine.py`
2. Ajuste os seletores CSS conforme necessário
3. Modifique a extração de dados

### Personalizar Interface CLI

1. Edite `cli.py`
2. Adicione novos comandos no `create_parser()`
3. Implemente os métodos correspondentes

## 🐛 Troubleshooting

### Erro: Chrome mostra muitos logs de GPU/WebGL
**Sintomas:** Aparecem várias mensagens de erro sobre GPU e WebGL durante a execução
**Solução:** O sistema executa em modo headless por padrão. Se quiser ver o navegador:
```bash
python main.py start --visual
```

### Erro: Sistema parece travado
**Sintomas:** Logs param de aparecer após "Acessando: https://..."
**Solução:** O scraping pode estar demorando. Aguarde alguns minutos ou use:
```bash
python main.py start --show-logs
```
Para ver se há progresso.

### Erro: Nenhum anúncio encontrado
**Sintomas:** "Nenhum anúncio encontrado" nos logs
**Solução:** 
1. Verifique se a palavra-chave tem anúncios no Facebook Marketplace
2. Teste com uma palavra-chave conhecida: `python main.py test "honda civic" santoandre`
3. Aguarde alguns minutos - o Facebook pode carregar anúncios lentamente

### Erro: Redirecionado para login
**Sintomas:** "Redirecionado para login do Facebook"
**Solução:** O Facebook detectou automação. Tente:
1. Aguardar algumas horas
2. Usar intervalos maiores entre verificações
3. Executar em horários diferentes

### Performance: Muito lento
**Solução:**
```bash
# Reduzir número de palavras-chave ativas
python main.py keyword list
python main.py keyword update ID --interval 300

# Aumentar delays
python main.py config --set request_delay_ms 3000
```

## 📊 Monitoramento e Logs

### Logs do Sistema
Os logs são salvos em:
- Console (tempo real)
- Banco de dados (tabela `system_logs`)
- Arquivos de notificação (se habilitados)

### Níveis de Log
- **INFO**: Operações normais
- **WARNING**: Situações que merecem atenção
- **ERROR**: Erros que impedem execução
- **SUCCESS**: Operações bem-sucedidas

### Métricas Coletadas
- Tempo de execução por busca
- Número de anúncios encontrados
- Taxa de sucesso/erro
- Performance por palavra-chave

## 🔒 Considerações de Segurança

- Respeita robots.txt e termos de uso
- Implementa delays realistas entre requests
- Não armazena dados pessoais dos usuários
- Logs não contêm informações sensíveis

## 📝 Licença

Este projeto é para fins educacionais e de pesquisa. Respeite os termos de uso do Facebook Marketplace.

## 🤝 Contribuição

1. Fork o projeto
2. Crie uma branch para sua feature
3. Commit suas mudanças
4. Push para a branch
5. Abra um Pull Request

## 📞 Suporte

Para problemas ou dúvidas:
1. Verifique os logs: `python main.py status`
2. Teste configuração: `python main.py test "termo" cidade`
3. Consulte a documentação do código
4. Abra uma issue no repositório
