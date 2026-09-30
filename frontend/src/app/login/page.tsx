"use client";
import Image from "next/image";
import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const router = useRouter();
  const [step, setStep] = useState<1 | 2>(1);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (step === 1) {
      setStep(2);
      return;
    }

    setLoading(true);

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/login`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password }),
        }
      );

      if (!response.ok) {
        setError("Email ou mot de passe incorrect");
        setLoading(false);
        return;
      }

      const data = await response.json();
      localStorage.setItem("access_token", data.access_token);
      router.push("/");
    } catch {
      setError("Impossible de contacter le serveur");
      setLoading(false);
    }
  }

  return (
    <div className="auth-background">
      <div className="login-card">
        <div className="login-logo">
        <Image
            src="/images/Logo.png"
            alt="NewsFoundry"
            width={200}
            height={50}
            className="login-logo-icon"
          />
        </div>
        <p className="login-subtitle">
          Connectez-vous pour accéder à votre assistant d&apos;actualités IA
        </p>

        <form onSubmit={handleSubmit}>
          <label htmlFor="email" className="login-label">
            Adresse email
          </label>
          <input
            id="email"
            type="email"
            required
            placeholder="votre.email@exemple.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={step === 2}
            className="login-input"
          />

          {step === 2 && (
            <>
              <label htmlFor="password" className="login-label">
                Mot de passe
              </label>
              <input
                id="password"
                type="password"
                required
                autoFocus
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="login-input"
              />
            </>
          )}

          {error && <p className="login-error">{error}</p>}

          <button type="submit" disabled={loading} className="login-button">
            {loading ? "Connexion..." : "Se connecter"}
          </button>
        </form>
      </div>
    </div>
  );
}