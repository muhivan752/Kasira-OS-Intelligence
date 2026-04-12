import { NextResponse } from 'next/server';
import { readFile } from 'fs/promises';
import { existsSync } from 'fs';

const PATHS = [
  '/app/public/apk/kasira-dapur.apk',
  '/app/.next/standalone/public/apk/kasira-dapur.apk',
];

const FALLBACK = 'https://github.com/muhivan752/Kasira-OS-Intelligence/releases/latest';

export async function GET() {
  for (const p of PATHS) {
    if (existsSync(p)) {
      const file = await readFile(p);
      return new NextResponse(file, {
        headers: {
          'Content-Type': 'application/vnd.android.package-archive',
          'Content-Disposition': 'attachment; filename="kasira-dapur.apk"',
          'Content-Length': file.byteLength.toString(),
        },
      });
    }
  }
  return NextResponse.redirect(FALLBACK, 302);
}
