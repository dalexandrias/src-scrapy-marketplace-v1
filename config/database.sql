-- Schema do banco de dados SQLite para monitoramento do Facebook Marketplace
-- Versão: 1.0
-- Data: 2025-08-30

-- Tabela de configurações gerais do sistema
CREATE TABLE IF NOT EXISTS config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT UNIQUE NOT NULL,
    value TEXT NOT NULL,
    description TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de cidades monitoradas
CREATE TABLE IF NOT EXISTS cities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    facebook_slug TEXT UNIQUE NOT NULL,
    active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de palavras-chave para monitoramento
CREATE TABLE IF NOT EXISTS keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    term TEXT NOT NULL,
    active BOOLEAN DEFAULT 1,
    check_interval INTEGER DEFAULT 120, -- segundos entre verificações
    last_check DATETIME,
    total_checks INTEGER DEFAULT 0,
    total_found INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de anúncios encontrados
CREATE TABLE IF NOT EXISTS listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    facebook_id TEXT UNIQUE NOT NULL,
    title TEXT,
    price TEXT,
    url TEXT NOT NULL,
    description TEXT,
    location TEXT,
    image_url TEXT,
    city_id INTEGER,
    keyword_id INTEGER,
    found_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    notified BOOLEAN DEFAULT 0,
    notified_at DATETIME,
    FOREIGN KEY (city_id) REFERENCES cities(id) ON DELETE SET NULL,
    FOREIGN KEY (keyword_id) REFERENCES keywords(id) ON DELETE SET NULL
);

-- Tabela de logs do sistema
CREATE TABLE IF NOT EXISTS system_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    level TEXT NOT NULL CHECK (level IN ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')),
    message TEXT NOT NULL,
    module TEXT,
    function TEXT,
    details TEXT, -- JSON com detalhes adicionais
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de notificações enviadas
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id INTEGER,
    type TEXT NOT NULL, -- console, file, email, webhook
    status TEXT DEFAULT 'pending', -- pending, sent, failed
    message TEXT,
    error_message TEXT,
    sent_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (listing_id) REFERENCES listings(id) ON DELETE CASCADE
);

-- Tabela de estatísticas de execução
CREATE TABLE IF NOT EXISTS execution_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword_id INTEGER,
    city_id INTEGER,
    execution_time_ms INTEGER,
    listings_found INTEGER,
    new_listings INTEGER,
    errors INTEGER,
    executed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (keyword_id) REFERENCES keywords(id) ON DELETE CASCADE,
    FOREIGN KEY (city_id) REFERENCES cities(id) ON DELETE CASCADE
);

-- Índices para otimização
CREATE INDEX IF NOT EXISTS idx_listings_facebook_id ON listings(facebook_id);
CREATE INDEX IF NOT EXISTS idx_listings_found_at ON listings(found_at);
CREATE INDEX IF NOT EXISTS idx_listings_city_keyword ON listings(city_id, keyword_id);
CREATE INDEX IF NOT EXISTS idx_keywords_active ON keywords(active);
CREATE INDEX IF NOT EXISTS idx_keywords_last_check ON keywords(last_check);
CREATE INDEX IF NOT EXISTS idx_cities_active ON cities(active);
CREATE INDEX IF NOT EXISTS idx_system_logs_level ON system_logs(level);
CREATE INDEX IF NOT EXISTS idx_system_logs_created_at ON system_logs(created_at);

-- Triggers para atualizar updated_at automaticamente
CREATE TRIGGER IF NOT EXISTS update_config_timestamp 
    AFTER UPDATE ON config
    BEGIN
        UPDATE config SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

CREATE TRIGGER IF NOT EXISTS update_cities_timestamp 
    AFTER UPDATE ON cities
    BEGIN
        UPDATE cities SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

CREATE TRIGGER IF NOT EXISTS update_keywords_timestamp 
    AFTER UPDATE ON keywords
    BEGIN
        UPDATE keywords SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

-- Dados iniciais de configuração
INSERT OR IGNORE INTO config (key, value, description) VALUES 
('check_interval_default', '120', 'Intervalo padrão entre verificações em segundos'),
('max_retries', '3', 'Número máximo de tentativas em caso de erro'),
('timeout_request', '30', 'Timeout para requisições HTTP em segundos'),
('notification_enabled', 'true', 'Habilitar notificações'),
('notification_types', 'console,file', 'Tipos de notificação separados por vírgula'),
('log_level', 'INFO', 'Nível de log do sistema'),
('headless_browser', 'true', 'Executar navegador em modo headless'),
('max_listings_per_check', '50', 'Máximo de anúncios para processar por verificação'),
('cleanup_logs_days', '30', 'Dias para manter logs antigos'),
('database_version', '1.0', 'Versão do schema do banco de dados');

-- Cidades padrão
INSERT OR IGNORE INTO cities (name, facebook_slug) VALUES 
('Santo André', 'santoandre'),
('São Paulo', 'saopaulo'),
('São Bernardo do Campo', 'saobernardodocampo'),
('São Caetano do Sul', 'saocaetanodosul'),
('Diadema', 'diadema'),
('Mauá', 'maua'),
('Ribeirão Pires', 'ribeirapires');

-- Palavras-chave padrão
INSERT OR IGNORE INTO keywords (term, check_interval) VALUES 
('honda civic', 120),
('toyota corolla', 120),
('volkswagen golf', 120),
('ford focus', 180),
('chevrolet cruze', 180);
