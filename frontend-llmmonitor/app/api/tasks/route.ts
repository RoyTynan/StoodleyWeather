import { NextRequest, NextResponse } from 'next/server';
import { listTasks, countTasks, deleteAllPrompts } from '@/lib/db';

export const dynamic = 'force-dynamic';

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const limit = parseInt(searchParams.get('limit') ?? '10');
  const offset = parseInt(searchParams.get('offset') ?? '0');

  const tasks = listTasks(limit, offset);
  const total = countTasks();

  return NextResponse.json({ tasks, total });
}

export async function DELETE() {
  const count = deleteAllPrompts();
  return NextResponse.json({ deleted: count });
}
