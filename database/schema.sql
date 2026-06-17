CREATE TABLE IF NOT EXISTS scans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    arquivo_nome TEXT,
    link_busca TEXT,
    origem TEXT,
    destino TEXT,
    data_viagem TEXT,
    sentido TEXT,
    status_validacao TEXT NOT NULL,
    observacoes TEXT
);

CREATE TABLE IF NOT EXISTS motoristas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_id INTEGER NOT NULL,
    nome_motorista TEXT,
    horario TEXT,
    preco REAL,
    vagas TEXT,
    status TEXT,
    eh_ezequiel INTEGER DEFAULT 0,
    eh_barbosa INTEGER DEFAULT 0,
    contexto TEXT,
    FOREIGN KEY (scan_id) REFERENCES scans(id)
);

CREATE TABLE IF NOT EXISTS decisoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_id INTEGER NOT NULL,
    acao TEXT NOT NULL,
    conta TEXT,
    origem TEXT,
    destino_final TEXT,
    intermediarias TEXT,
    data TEXT,
    horario TEXT,
    preco_sugerido TEXT,
    risco_conflito TEXT,
    status_validacao TEXT NOT NULL,
    motivo TEXT,
    FOREIGN KEY (scan_id) REFERENCES scans(id)
);

CREATE TABLE IF NOT EXISTS agenda (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data_viagem TEXT NOT NULL,
    dia_semana TEXT,
    sentido TEXT,
    origem TEXT,
    destino_final TEXT,
    horario_planejado TEXT,
    conta TEXT,
    status TEXT,
    prioridade TEXT,
    observacoes TEXT
);
