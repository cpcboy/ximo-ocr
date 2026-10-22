import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "墨析 · 本地 OCR 工作台",
  description:
    "在本机批量识别图片、PDF、Office 文档与压缩包，文件无需上传外网。",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
