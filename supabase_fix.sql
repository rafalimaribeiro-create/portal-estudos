-- =============================================================
-- DIAGNÓSTICO + CORREÇÃO COMPLETA DO TRACKER
-- Execute no SQL Editor do Supabase (project qseismabfaonggrwzuiu)
-- =============================================================

-- 1. DIAGNÓSTICO: quantas linhas existem na tabela?
SELECT COUNT(*) AS total_linhas FROM public.progress;

-- 2. DIAGNÓSTICO: quais políticas RLS existem?
SELECT policyname, cmd, qual, with_check
FROM pg_policies
WHERE tablename = 'progress';

-- 3. DIAGNÓSTICO: quais constraints existem?
SELECT conname, contype
FROM pg_constraint
WHERE conrelid = 'public.progress'::regclass;

-- =============================================================
-- CORREÇÃO (execute as linhas abaixo após o diagnóstico)
-- =============================================================

-- 4. Garantir que a tabela tenha a constraint UNIQUE necessária
--    (sem ela o upsert pode falhar silenciosamente em algumas versões)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid = 'public.progress'::regclass
      AND contype = 'u'
      AND conname = 'progress_user_chapter_unique'
  ) THEN
    ALTER TABLE public.progress
    ADD CONSTRAINT progress_user_chapter_unique UNIQUE (user_id, chapter_id);
    RAISE NOTICE 'Constraint UNIQUE criada.';
  ELSE
    RAISE NOTICE 'Constraint UNIQUE já existe.';
  END IF;
END $$;

-- 5. Habilitar RLS (caso não esteja)
ALTER TABLE public.progress ENABLE ROW LEVEL SECURITY;

-- 6. Remover políticas antigas (se existirem) para recriar do zero
DROP POLICY IF EXISTS "Users can manage own progress" ON public.progress;
DROP POLICY IF EXISTS "Users own progress"             ON public.progress;
DROP POLICY IF EXISTS "progress_policy"                ON public.progress;
DROP POLICY IF EXISTS "progress_select"                ON public.progress;
DROP POLICY IF EXISTS "progress_insert"                ON public.progress;
DROP POLICY IF EXISTS "progress_update"                ON public.progress;
DROP POLICY IF EXISTS "progress_delete"                ON public.progress;

-- 7. Criar políticas separadas para cada operação
--    SELECT sem USING retorna 0 linhas — esta é a causa mais comum do tracker zerado!
CREATE POLICY "progress_select" ON public.progress
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "progress_insert" ON public.progress
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "progress_update" ON public.progress
  FOR UPDATE USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "progress_delete" ON public.progress
  FOR DELETE USING (auth.uid() = user_id);

-- 8. Verificação final: listar as políticas criadas
SELECT policyname, cmd FROM pg_policies WHERE tablename = 'progress';
