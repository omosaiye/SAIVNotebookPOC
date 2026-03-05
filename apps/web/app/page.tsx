"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { readSession } from "../lib/session";

export default function HomePage() {
  const router = useRouter();

  useEffect(() => {
    const session = readSession();
    if (session) {
      router.replace("/workspace");
      return;
    }
    router.replace("/login");
  }, [router]);

  return null;
}
