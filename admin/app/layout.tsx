import type { Metadata } from "next";
import "./styles.css";

export const metadata: Metadata = {
  title: "ForgeMind Admin",
  description: "Guidance, safety, memory, and prompt operations for ForgeMind"
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
