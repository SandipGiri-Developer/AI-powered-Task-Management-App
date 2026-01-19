-- Updated SQL Schema with all necessary fields for task management system
-- Copy and execute this in your Supabase SQL editor

-- 1. Users Table (Stores who is who)
CREATE TABLE IF NOT EXISTS users (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  full_name TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('manager', 'employee')),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- 2. Tasks Table (Stores the work)
CREATE TABLE IF NOT EXISTS tasks (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  title TEXT NOT NULL,
  description TEXT,
  assigned_to UUID REFERENCES users(id) ON DELETE CASCADE,
  assigned_by UUID REFERENCES users(id) ON DELETE CASCADE,
  due_date TIMESTAMP WITH TIME ZONE,
  progress INT DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'in_progress')),
  warning_sent BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
  completed_at TIMESTAMP WITH TIME ZONE
);

-- Create indexes on tasks table
CREATE INDEX IF NOT EXISTS idx_tasks_assigned_to ON tasks(assigned_to);
CREATE INDEX IF NOT EXISTS idx_tasks_assigned_by ON tasks(assigned_by);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at);

-- 3. Messages/Notifications Table (Stores the AI messages and alerts)
CREATE TABLE IF NOT EXISTS messages (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  recipient_id UUID REFERENCES users(id) ON DELETE CASCADE,
  content TEXT NOT NULL,
  is_read BOOLEAN DEFAULT FALSE,
  message_type TEXT CHECK (message_type IN ('new_task', 'warning', 'completion', 'general')),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- Create indexes on messages table
CREATE INDEX IF NOT EXISTS idx_messages_recipient_id ON messages(recipient_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);

-- Optional: Add RLS (Row Level Security) policies if using Supabase auth
-- Enable RLS on tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see themselves
CREATE POLICY "Users can view their own data" ON users
  FOR SELECT USING (auth.uid() = id);

-- Policy: Users can only see tasks assigned to them or assigned by them
CREATE POLICY "Users can view relevant tasks" ON tasks
  FOR SELECT USING (
    assigned_to = auth.uid() OR assigned_by = auth.uid()
  );

-- Policy: Users can only see messages sent to them
CREATE POLICY "Users can view own messages" ON messages
  FOR SELECT USING (recipient_id = auth.uid());
