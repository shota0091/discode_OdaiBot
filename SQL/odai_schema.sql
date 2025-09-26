
-- サーバー情報（ギルド）
CREATE TABLE guilds (
    id BIGINT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    remind_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- チャンネル情報（リマインド送信先）
CREATE TABLE channels (
    id BIGINT PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    name VARCHAR(100),
    is_remind_target BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (guild_id) REFERENCES guilds(id) ON DELETE CASCADE
);

-- お題（画像 or 文字 or 両方）
CREATE TABLE odai_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    channel_id BIGINT,
    content TEXT NOT NULL,
    image_path VARCHAR(255),
    is_sent BOOLEAN DEFAULT FALSE,
    created_by BIGINT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (guild_id) REFERENCES guilds(id) ON DELETE CASCADE,
    FOREIGN KEY (channel_id) REFERENCES channels(id) ON DELETE SET NULL
);

-- 画像ファイル（お題に使う用）
CREATE TABLE image_files (
    id INT AUTO_INCREMENT PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    filename VARCHAR(255) NOT NULL,
    is_sent BOOLEAN DEFAULT FALSE,
    created_by BIGINT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (guild_id) REFERENCES guilds(id) ON DELETE CASCADE
);
