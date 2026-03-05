"use client";

import { FormEvent, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { fetchProfile, login } from "../../lib/api";
import { saveSession } from "../../lib/session";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("owner@local.dev");
  const [password, setPassword] = useState("dev-password");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canSubmit = useMemo(() => {
    return email.trim().length > 0 && password.trim().length > 0 && !isLoading;
  }, [email, password, isLoading]);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSubmit) {
      return;
    }

    setError(null);
    setIsLoading(true);
    try {
      const result = await login(email.trim(), password);
      const primaryWorkspace = result.workspaceIds[0];
      if (!primaryWorkspace) {
        throw new Error("User has no assigned workspaces.");
      }

      saveSession({
        accessToken: result.accessToken,
        userId: result.userId,
        email: result.email,
        workspaceIds: result.workspaceIds,
        activeWorkspaceId: primaryWorkspace
      });

      await fetchProfile({
        accessToken: result.accessToken,
        userId: result.userId,
        email: result.email,
        workspaceIds: result.workspaceIds,
        activeWorkspaceId: primaryWorkspace
      });

      router.replace("/workspace");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Login failed");
      setIsLoading(false);
    }
  }

  return (
    <main className="page-wrap" style={{ minHeight: "100vh", display: "grid", alignItems: "center" }}>
      <section className="surface" style={{ maxWidth: 480, margin: "0 auto", padding: 28 }}>
        <header style={{ marginBottom: 18 }}>
          <p style={{ margin: 0, color: "var(--ink-muted)", letterSpacing: 0.4 }}>Private LLM Workspace</p>
          <h1 style={{ margin: "4px 0 0", fontSize: 34, lineHeight: 1.1 }}>Sign In</h1>
        </header>

        <form onSubmit={onSubmit} style={{ display: "grid", gap: 12 }}>
          <label style={{ display: "grid", gap: 8 }}>
            <span>Email</span>
            <input className="field" type="email" value={email} onChange={(event) => setEmail(event.target.value)} />
          </label>
          <label style={{ display: "grid", gap: 8 }}>
            <span>Password</span>
            <input
              className="field"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </label>

          {error ? (
            <p role="alert" style={{ margin: "2px 0 0", color: "var(--danger)" }}>
              {error}
            </p>
          ) : null}

          <button className="button brand" type="submit" disabled={!canSubmit}>
            {isLoading ? "Signing in..." : "Sign in"}
          </button>
        </form>
      </section>
    </main>
  );
}

