ALTER TABLE progress
ADD CONSTRAINT progress_user_chapter_unique
UNIQUE (user_id, chapter_id);
