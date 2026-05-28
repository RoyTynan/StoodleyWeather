import { NextResponse } from 'next/server';
import { listAutocompTasks, countAutocompTasks } from '@/lib/db';

export const dynamic = 'force-dynamic';

export async function GET() {
  const tasks = listAutocompTasks();
  const total = countAutocompTasks();
  return NextResponse.json({ tasks, total });
}
