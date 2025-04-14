-- Схема базы данных для API чат-бота

-- Пользователи
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    email VARCHAR(100) UNIQUE,
    telegram_id BIGINT UNIQUE,
    referral_code VARCHAR(10) UNIQUE,
    referrer_id VARCHAR(36),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (referrer_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Тарифные планы
CREATE TABLE IF NOT EXISTS plans (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    description TEXT,
    price DECIMAL(10, 2) NOT NULL,
    requests_allowed INT NOT NULL,
    duration_days INT DEFAULT 30,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Подписки пользователей
CREATE TABLE IF NOT EXISTS user_plans (
    user_id VARCHAR(36) NOT NULL,
    plan_id INT NOT NULL,
    start_date DATETIME NOT NULL,
    end_date DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE
);

-- Запросы пользователей
CREATE TABLE IF NOT EXISTS requests (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    query TEXT NOT NULL,
    response TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Платежи
CREATE TABLE IF NOT EXISTS payments (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    plan_id INT NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    payment_details TEXT,
    promo_code VARCHAR(20),
    status VARCHAR(20) DEFAULT 'completed',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE
);

-- Промокоды
CREATE TABLE IF NOT EXISTS promo_codes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(20) NOT NULL UNIQUE,
    discount DECIMAL(5, 2) NOT NULL,
    valid_until DATETIME,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

    -- Создание таблицы для чатов
    CREATE TABLE IF NOT EXISTS chats (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,            -- Соответствует user_id в таблице users
        title VARCHAR(255) DEFAULT 'Новый чат',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE -- Связь с таблицей пользователей
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

    -- Создание таблицы для сообщений чата
    CREATE TABLE IF NOT EXISTS chat_messages (
        id INT AUTO_INCREMENT PRIMARY KEY,
        chat_id INT NOT NULL,           -- Соответствует id в таблице chats
        role VARCHAR(10) NOT NULL,      -- 'user' или 'assistant'
        content TEXT NOT NULL,
        model_used VARCHAR(100) NULL,   -- Модель ИИ (если role='assistant')
        tokens_used INT NULL,           -- Потраченные токены (если role='assistant')
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (chat_id) REFERENCES chats(id) ON DELETE CASCADE -- Связь с таблицей чатов
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

    -- Дополнительно: Индексы для ускорения запросов (рекомендуется)



-- Начальные данные для тарифных планов
INSERT INTO plans (name, description, price, requests_allowed, duration_days) VALUES
('Базовый', 'Доступ к базовым функциям бота', 299.00, 50, 30),
('Стандарт', 'Расширенный доступ с большим количеством запросов', 799.00, 200, 30),
('Премиум', 'Полный доступ ко всем функциям без ограничений', 1499.00, 500, 30);

-- Индексы для оптимизации запросов
CREATE INDEX idx_requests_user_id ON requests(user_id);
CREATE INDEX idx_payments_user_id ON payments(user_id);
CREATE INDEX idx_user_plans_plan_id ON user_plans(plan_id); 
CREATE INDEX idx_chats_user_id ON chats(user_id);
CREATE INDEX idx_chat_messages_chat_id ON chat_messages(chat_id);
CREATE INDEX idx_chat_messages_timestamp ON chat_messages(timestamp);