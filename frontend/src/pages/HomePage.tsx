import { Link } from "react-router-dom";
import { ShieldCheck, Building2, Search, ArrowRight } from "lucide-react";

const HomePage = () => {
  return (
    <div className="relative">
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[600px] h-[600px] rounded-full bg-primary/5 blur-[120px]" />
      </div>

      <section className="container relative flex flex-col items-center justify-center min-h-[calc(100vh-4rem)] py-24 text-center">
        <div className="animate-fade-up inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-border/50 bg-secondary/50 text-sm text-muted-foreground mb-8">
          <ShieldCheck className="h-4 w-4 text-primary" />
          Cryptographic certificate verification for institutions
        </div>

        <h1 className="animate-fade-up-delay-1 text-balance max-w-3xl text-5xl font-extrabold leading-[1.08] tracking-tight sm:text-6xl lg:text-7xl">
          Academic Certificate{" "}
          <span className="text-primary">Verification</span>
        </h1>

        <p className="animate-fade-up-delay-2 mt-6 max-w-xl text-lg text-muted-foreground text-pretty leading-relaxed">
          Issue PDF credentials with SHA-256 integrity and RSA signatures, then let anyone verify by ID or by uploading
          the file.
        </p>

        <div className="animate-fade-up-delay-3 mt-16 grid w-full max-w-2xl gap-6 sm:grid-cols-2">
          <div className="glass-card glow-blue p-8 text-left transition-all duration-200 hover:border-primary/40 hover:bg-card/90">
            <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10">
              <Building2 className="h-6 w-6 text-primary" />
            </div>
            <h3 className="text-lg font-semibold">For Institutions</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              Register to issue tamper-proof certificates with QR codes.
            </p>
            <Link
              to="/login"
              className="mt-6 inline-flex items-center gap-1 rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground hover:bg-primary/90 transition-colors active:scale-[0.98]"
            >
              Register / Login
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>

          <div className="glass-card p-8 text-left transition-all duration-200 hover:border-primary/40 hover:bg-card/90">
            <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10">
              <Search className="h-6 w-6 text-primary" />
            </div>
            <h3 className="text-lg font-semibold">For Verifiers</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              Instantly verify any certificate — no login required.
            </p>
            <Link
              to="/verify"
              className="mt-6 inline-flex items-center gap-1 rounded-lg border border-input px-4 py-2.5 text-sm font-semibold hover:bg-secondary transition-colors active:scale-[0.98]"
            >
              Verify now
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
};

export default HomePage;
