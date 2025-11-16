-- Таблица для квиза НЕ-психологов: упущенный потенциал
CREATE TABLE IF NOT EXISTS non_psych_quiz_results (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    quiz_id INTEGER NOT NULL REFERENCES quizzes(id),
    is_psychologist_snapshot BOOLEAN NOT NULL DEFAULT FALSE,

    -- сырые ответы
    months_in_psychology INTEGER NOT NULL,
    frequency_coef INTEGER NOT NULL,
    sabotage_items_count INTEGER NOT NULL,
    sabotage_items_codes VARCHAR,

    -- расчётные поля
    days_in_psychology INTEGER NOT NULL,
    thoughts_count INTEGER NOT NULL,
    sabotage_forms_total INTEGER NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для быстрого поиска
CREATE INDEX IF NOT EXISTS idx_non_psych_quiz_results_user_id
    ON non_psych_quiz_results(user_id);

CREATE INDEX IF NOT EXISTS idx_non_psych_quiz_results_created_at
    ON non_psych_quiz_results(created_at);
