-- Таблица событий пользователя для аналитики
CREATE TABLE IF NOT EXISTS user_events (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    quiz_id INTEGER REFERENCES quizzes(id),
    event_code VARCHAR NOT NULL,
    payload JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы
CREATE INDEX IF NOT EXISTS idx_user_events_user_id ON user_events(user_id);
CREATE INDEX IF NOT EXISTS idx_user_events_created_at ON user_events(created_at);
CREATE INDEX IF NOT EXISTS idx_user_events_event_code ON user_events(event_code);
