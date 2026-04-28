import { NextResponse } from 'next/server';
import { getLatestConfig } from '@/lib/db';

export const dynamic = 'force-dynamic';

export async function GET() {
  const config = getLatestConfig();
  if (!config) {
    return NextResponse.json({ error: 'No config snapshot found — restart the proxy' }, { status: 404 });
  }
  return NextResponse.json(config);
}
