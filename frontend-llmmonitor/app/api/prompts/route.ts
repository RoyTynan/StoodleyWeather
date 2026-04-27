import { NextRequest, NextResponse } from 'next/server';
import { listPrompts, countPrompts, deleteAllPrompts } from '@/lib/db';

export const dynamic = 'force-dynamic';

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const limit = parseInt(searchParams.get('limit') ?? '100');
  const offset = parseInt(searchParams.get('offset') ?? '0');

  const prompts = listPrompts(limit, offset);
  const total = countPrompts();

  return NextResponse.json({ prompts, total });
}

export async function DELETE() {
  const count = deleteAllPrompts();
  return NextResponse.json({ deleted: count });
}
