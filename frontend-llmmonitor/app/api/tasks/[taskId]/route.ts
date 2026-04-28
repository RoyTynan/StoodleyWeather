import { NextRequest, NextResponse } from 'next/server';
import { deleteTask } from '@/lib/db';

export const dynamic = 'force-dynamic';

export async function DELETE(
  _request: NextRequest,
  { params }: { params: { taskId: string } }
) {
  const count = deleteTask(params.taskId);
  return NextResponse.json({ deleted: count });
}
