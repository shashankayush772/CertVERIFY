import { Link, useLocation } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { ShieldCheck, LogOut, User } from "lucide-react";

const Navbar = () => {
  const { isLoggedIn, role, email, logout } = useAuth();
  const location = useLocation();

  const navLinks = [
    { to: "/", label: "Home" },
    { to: "/verify", label: "Verify" },
    ...(isLoggedIn && role === "institution" ? [{ to: "/upload", label: "Issue" }] : []),
  ];

  /** Show the part before '@' as display name, fallback to full email. */
  const displayName = email ? email.split("@")[0] : "User";
  const roleBadge = role === "institution" ? "Institution" : role === "verifier" ? "Verifier" : "";

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 border-b border-border/50 bg-background/80 backdrop-blur-xl">
      <div className="container flex h-16 items-center justify-between">
        <Link to="/" className="flex items-center gap-2 group">
          <ShieldCheck className="h-6 w-6 text-primary transition-transform group-hover:scale-110 group-active:scale-95" />
          <span className="text-lg font-bold tracking-tight">CertVerify</span>
        </Link>

        <div className="flex items-center gap-1">
          {navLinks.map((link) => (
            <Link
              key={link.to}
              to={link.to}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                location.pathname === link.to
                  ? "text-foreground bg-secondary"
                  : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
              }`}
            >
              {link.label}
            </Link>
          ))}

          {isLoggedIn ? (
            <div className="ml-3 flex items-center gap-3">
              {/* User greeting */}
              <div className="flex items-center gap-2.5">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/15 border border-primary/30">
                  <User className="h-4 w-4 text-primary" />
                </div>
                <div className="hidden sm:flex flex-col leading-none">
                  <span className="text-sm font-medium text-foreground">
                    Hello, {displayName}
                  </span>
                  {roleBadge && (
                    <span className="mt-0.5 text-[11px] font-medium text-primary/80">
                      {roleBadge}
                    </span>
                  )}
                </div>
              </div>

              {/* Logout button */}
              <button
                type="button"
                onClick={logout}
                className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-secondary/50 transition-colors active:scale-95"
              >
                <LogOut className="h-4 w-4" />
                <span className="hidden sm:inline">Logout</span>
              </button>
            </div>
          ) : (
            <Link
              to="/login"
              className="ml-2 px-4 py-2 rounded-lg text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/90 transition-colors active:scale-95"
            >
              Login
            </Link>
          )}
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
