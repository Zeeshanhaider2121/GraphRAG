import { useState } from "react";
import Button from "../components/Button";
import Input from "../components/Input";

function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");

  const handleSubmit = (event) => {
    event.preventDefault();
    setMessage("Login UI is ready. Connect auth flow to backend token endpoint if needed.");
  };

  return (
    <section className="mx-auto max-w-md px-4 py-8 sm:px-6 lg:px-8">
      <article className="rounded-3xl border border-border bg-card/95 p-6 shadow-soft sm:p-8">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-muted">Account</p>
        <h1 className="mt-2 text-2xl font-bold text-ink">Login</h1>
        <p className="mt-2 text-sm text-muted">Access your GraphRAG workspace.</p>

        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          <Input
            label="Username"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            placeholder="Enter username"
            required
          />
          <Input
            label="Password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="Enter password"
            type="password"
            required
          />
          <Button type="submit" className="w-full">
            Login
          </Button>
        </form>

        {message ? (
          <p className="mt-4 rounded-xl bg-accent-soft px-3 py-2 text-sm font-medium text-accent">
            {message}
          </p>
        ) : null}
      </article>
    </section>
  );
}

export default LoginPage;
