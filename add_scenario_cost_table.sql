-- Создание таблицы для результатов расчета стоимости сценария
CREATE TABLE IF NOT EXISTS scenario_cost_results (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    quiz_id INTEGER NOT NULL REFERENCES quizzes(id),
    is_psychologist_snapshot BOOLEAN NOT NULL DEFAULT TRUE,
    scenario VARCHAR(50),  -- 'impostor', 'eternal_student', 'seeker'
    expected_income INTEGER NOT NULL,
    current_income INTEGER NOT NULL,
    months_delay INTEGER NOT NULL,
    lost_per_month INTEGER NOT NULL,
    lost_total INTEGER NOT NULL,
    lost_3_years INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Создаем индексы для быстрого поиска
CREATE INDEX IF NOT EXISTS idx_scenario_cost_results_user_id ON scenario_cost_results(user_id);
CREATE INDEX IF NOT EXISTS idx_scenario_cost_results_created_at ON scenario_cost_results(created_at);