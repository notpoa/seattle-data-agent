import type { Metadata } from 'next';
import './style.css';
export const metadata: Metadata = { title: 'Seattle Data Agent', description: 'Ask a question. Explore official Seattle public data.' };
export default function Layout({ children }: { children: React.ReactNode }) {
  return <html lang="en"><body>{children}</body></html>;
}
