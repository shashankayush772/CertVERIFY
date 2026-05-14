import { useCallback, useEffect, useState, useRef } from "react";
import {
  Search,
  Upload,
  ShieldCheck,
  FileText,
  XCircle,
  CheckCircle2,
  AlertTriangle,
  Link,
} from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import api, { formatApiError } from "@/lib/api";

const VerifyPage = () => {
  const { isLoggedIn, role } = useAuth();
  const [activeTab, setActiveTab] = useState<"id" | "upload">("id");
  const [historyTick, setHistoryTick] = useState(0);

  const bumpHistory = useCallback(() => setHistoryTick((t) => t + 1), []);

  return (
    <div className="container max-w-2xl py-12">
      <div className="animate-fade-up mb-8">
        <h1 className="text-3xl font-bold">Verify a Certificate</h1>
        <p className="mt-2 text-muted-foreground">
          Look up public record by ID or upload a PDF to verify hash and digital signature.
        </p>
      </div>

      <div className="animate-fade-up-delay-1">
        <div className="mb-6 flex rounded-lg border border-border bg-secondary/30 p-1">
          <button
            type="button"
            onClick={() => setActiveTab("id")}
            className={`flex-1 rounded-md px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === "id"
                ? "bg-card text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            Verify by ID
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("upload")}
            className={`flex-1 rounded-md px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === "upload"
                ? "bg-card text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            Verify by Upload
          </button>
        </div>

        {activeTab === "id" ? <VerifyById /> : <VerifyByUpload onVerified={bumpHistory} />}
      </div>

      {isLoggedIn && role === "verifier" ? (
        <VerifierHistory refreshKey={historyTick} />
      ) : null}
    </div>
  );
};

interface PublicCert {
  student_name: string;
  degree: string;
  institution_name: string;
  issue_date: string;
  status: string;
  cert_hash: string;
}

function formatDisplayDate(iso: string) {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function VerifyById() {
  const [certId, setCertId] = useState("");
  const [loading, setLoading] = useState(false);
  const [details, setDetails] = useState<PublicCert | null>(null);
  const [error, setError] = useState("");

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setDetails(null);
    setLoading(true);

    const id = certId.trim();
    if (!/^\d+$/.test(id)) {
      setError("Enter a numeric certificate ID.");
      setLoading(false);
      return;
    }

    try {
      const { data } = await api.get<PublicCert>(`/verify/${id}`);
      setDetails(data);
    } catch (err: unknown) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <form onSubmit={handleVerify} className="flex gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            required
            value={certId}
            onChange={(e) => setCertId(e.target.value)}
            placeholder="Enter Certificate ID"
            className="w-full rounded-lg border border-input bg-background/50 pl-10 pr-4 py-2.5 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring transition-shadow"
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          className="rounded-lg bg-primary px-6 py-2.5 text-sm font-semibold text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors active:scale-[0.98]"
        >
          {loading ? "..." : "Verify"}
        </button>
      </form>

      {error && (
        <div className="rounded-lg bg-destructive/10 border border-destructive/20 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {details && (
        <div className="animate-fade-up glass-card p-6 space-y-3">
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-success" />
            Certificate Details
          </h3>
          <div className="grid gap-3 text-sm">
            {(
              [
                ["Student", details.student_name],
                ["Degree", details.degree],
                ["Institution", details.institution_name],
                ["Issued", formatDisplayDate(details.issue_date)],
                ["Status", details.status],
                ["SHA-256", details.cert_hash],
              ] as const
            ).map(([label, value]) => (
              <div
                key={label}
                className="flex flex-col gap-1 border-b border-border/50 pb-2 sm:flex-row sm:justify-between sm:items-start"
              >
                <span className="text-muted-foreground shrink-0">{label}</span>
                <span className="font-medium text-right sm:text-left break-all">{value}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Check row helper ─────────────────────────────────────────────────────────
interface CheckRowProps {
  label: string;
  status: string;
  detail?: string;
  explorerUrl?: string;
}

function CheckRow({ label, status, detail, explorerUrl }: CheckRowProps) {
  const isPassed = status === "PASSED" || status === "VERIFIED";
  const isFailed = status === "FAILED" || status === "MISMATCH" || status === "REVOKED";
  const isDisabled = status === "DISABLED" || status === "NOT_REACHED" || status === "NOT_FOUND";

  return (
    <div className="flex items-start justify-between gap-2 text-sm py-1">
      <span className="text-muted-foreground shrink-0 w-44">{label}</span>
      <div className="flex flex-col items-end gap-0.5 text-right">
        <span
          className={
            isPassed
              ? "font-semibold text-success"
              : isFailed
              ? "font-semibold text-destructive"
              : "font-medium text-muted-foreground"
          }
        >
          {isPassed ? "✓ " : isFailed ? "✗ " : "— "}
          {detail || status}
        </span>
        {explorerUrl && isPassed && (
          <a
            href={explorerUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-xs text-primary hover:underline"
          >
            <Link className="h-3 w-3" />
            View on Polygonscan
          </a>
        )}
      </div>
    </div>
  );
}

// ── Updated response type with checks and blockchain ─────────────────────────
interface CheckDetail {
  status: string;
  detail?: string;
  label?: string;
  confidence?: string;
  explorer_url?: string;
  matches?: boolean | null;
}

interface UploadVerifyResponse {
  verdict: string;
  reason?: string;
  forgery_label?: string | null;
  student_name?: string;
  degree?: string;
  institution_name?: string;
  issue_date?: string;
  cert_hash?: string;
  forgery_confidence?: number | null;
  blockchain_tx_hash?: string | null;
  checks?: {
    ai_forgery_detection?: CheckDetail;
    hash_integrity?: CheckDetail;
    rsa_signature?: CheckDetail;
    blockchain?: CheckDetail;
  };
}

function VerifyByUpload({ onVerified }: { onVerified: () => void }) {
  const [certId, setCertId] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<UploadVerifyResponse | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped) setFile(dropped);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;
    setLoading(true);
    setResult(null);
    setError("");

    const idNum = Number.parseInt(certId.trim(), 10);
    if (!Number.isFinite(idNum) || idNum <= 0) {
      setError("Enter a valid numeric certificate ID.");
      setLoading(false);
      return;
    }

    try {
      const formData = new FormData();
      formData.append("cert_id", String(idNum));
      formData.append("file", file);

      const { data } = await api.post<UploadVerifyResponse>("/verify/upload", formData);
      setResult(data);
      onVerified();
    } catch (err: unknown) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  const verdict = result?.verdict?.toUpperCase() ?? "";
  const conf = result?.forgery_confidence;
  const confPct =
    conf === null || conf === undefined ? null : Math.min(100, Math.max(0, conf * 100));
  const confPctStr = confPct !== null ? `${confPct.toFixed(1)}%` : "—";
  const fl = result?.forgery_label ?? "—";
  const checks = result?.checks;
  const showVerdict =
    !!result &&
    ["AUTHENTIC", "TAMPERED", "INVALID", "FORGED"].includes(verdict);

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div>
        <label className="mb-1.5 block text-sm font-medium">Certificate ID</label>
        <input
          required
          value={certId}
          onChange={(e) => setCertId(e.target.value)}
          placeholder="Enter Certificate ID"
          className="w-full rounded-lg border border-input bg-background/50 px-4 py-2.5 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring transition-shadow"
        />
      </div>

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`cursor-pointer rounded-xl border-2 border-dashed p-12 text-center transition-colors ${
          dragOver
            ? "border-primary bg-primary/5"
            : file
              ? "border-success/40 bg-success/5"
              : "border-border hover:border-primary/40 hover:bg-card/50"
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png"
          className="hidden"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
        />
        {file ? (
          <div className="flex flex-col items-center gap-2">
            <FileText className="h-10 w-10 text-success" />
            <p className="text-sm font-medium">{file.name}</p>
            <p className="text-xs text-muted-foreground">Click to change</p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2">
            <Upload className="h-10 w-10 text-muted-foreground" />
            <p className="text-sm font-medium">Upload certificate PDF or image</p>
            <p className="text-xs text-muted-foreground">
              Drag & drop or click to browse — PDF, JPG, PNG supported
            </p>
          </div>
        )}
      </div>

      {error ? (
        <div className="rounded-lg bg-destructive/10 border border-destructive/20 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      ) : null}

      <button
        type="submit"
        disabled={loading || !file}
        className="w-full rounded-lg bg-primary px-4 py-3 text-sm font-semibold text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors active:scale-[0.98]"
      >
        {loading ? "Verifying..." : "Verify Certificate"}
      </button>

      {showVerdict && result ? (
        <div className="animate-fade-up space-y-4">

          {/* ── FORGED ──────────────────────────────────────────────────── */}
          {verdict === "FORGED" ? (
            <div className="rounded-xl border-2 border-destructive/50 bg-destructive/10 p-8 text-center">
              <div className="mb-3 flex justify-center">
                <XCircle className="h-14 w-14 text-destructive" />
              </div>
              <p className="text-2xl font-extrabold tracking-tight text-destructive">
                FORGED DOCUMENT
              </p>
              <p className="mt-2 text-sm text-muted-foreground">
                Forgery type:{" "}
                <span className="font-semibold text-foreground">{fl}</span>
              </p>
              <p className="mt-2 text-sm text-muted-foreground">
                Model confidence:{" "}
                <span className="font-semibold text-foreground">{confPctStr}</span>
              </p>
              {result.reason ? (
                <p className="mt-3 text-sm text-destructive/90">{result.reason}</p>
              ) : null}
            </div>
          ) : null}

          {/* ── AUTHENTIC ───────────────────────────────────────────────── */}
          {verdict === "AUTHENTIC" ? (
            <div className="rounded-xl border-2 border-success/50 bg-success/10 p-8">
              <div className="mb-3 flex justify-center">
                <CheckCircle2 className="h-14 w-14 text-success" />
              </div>
              <p className="text-2xl font-extrabold tracking-tight text-success text-center">
                AUTHENTIC
              </p>

              {/* 4-layer check summary */}
              <div className="mt-5 border-t border-success/20 pt-4 space-y-1">
                <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">
                  Verification Layers
                </p>
                <CheckRow
                  label="AI Forgery Detection"
                  status={checks?.ai_forgery_detection?.status ?? "PASSED"}
                  detail={`No forgery detected (${confPctStr})`}
                />
                <CheckRow
                  label="SHA-256 Hash Integrity"
                  status={checks?.hash_integrity?.status ?? "PASSED"}
                  detail="Hash matches stored record"
                />
                <CheckRow
                  label="RSA Digital Signature"
                  status={checks?.rsa_signature?.status ?? "PASSED"}
                  detail="Institution key verified"
                />
                <CheckRow
                  label="Blockchain Anchor"
                  status={checks?.blockchain?.status ?? "DISABLED"}
                  detail={
                    checks?.blockchain?.status === "VERIFIED"
                      ? "Hash verified on Polygon"
                      : checks?.blockchain?.status === "DISABLED"
                      ? "Not configured"
                      : checks?.blockchain?.detail ?? "—"
                  }
                  explorerUrl={checks?.blockchain?.explorer_url}
                />
              </div>

              {/* Certificate details */}
              {result.student_name ? (
                <div className="mt-4 space-y-1 text-left text-sm border-t border-success/20 pt-4">
                  <p>
                    <span className="text-muted-foreground">Student: </span>
                    <span className="font-medium">{result.student_name}</span>
                  </p>
                  <p>
                    <span className="text-muted-foreground">Degree: </span>
                    <span className="font-medium">{result.degree}</span>
                  </p>
                  <p>
                    <span className="text-muted-foreground">Institution: </span>
                    <span className="font-medium">{result.institution_name}</span>
                  </p>
                  <p>
                    <span className="text-muted-foreground">Issued: </span>
                    <span className="font-medium">
                      {result.issue_date ? formatDisplayDate(result.issue_date) : "—"}
                    </span>
                  </p>
                  {result.blockchain_tx_hash ? (
                    <p className="pt-1">
                      <span className="text-muted-foreground">Blockchain TX: </span>
                      <a
                        href={`https://amoy.polygonscan.com/tx/${result.blockchain_tx_hash}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-mono text-xs text-primary hover:underline break-all"
                      >
                        {result.blockchain_tx_hash}
                      </a>
                    </p>
                  ) : null}
                </div>
              ) : null}
            </div>
          ) : null}

          {/* ── TAMPERED ────────────────────────────────────────────────── */}
          {verdict === "TAMPERED" ? (
            <div className="rounded-xl border-2 border-amber-500/50 bg-amber-500/10 p-8 text-center">
              <div className="mb-3 flex justify-center">
                <AlertTriangle className="h-14 w-14 text-amber-500" />
              </div>
              <p className="text-2xl font-extrabold tracking-tight text-amber-600 dark:text-amber-400">
                TAMPERED
              </p>
              <p className="mt-2 text-sm text-muted-foreground">
                This document was modified after issuance.
              </p>

              {/* Check summary for tampered */}
              <div className="mt-4 border-t border-amber-500/20 pt-4 space-y-1 text-left">
                <CheckRow
                  label="AI Forgery Detection"
                  status={checks?.ai_forgery_detection?.status ?? "PASSED"}
                  detail={`AI signal: ${fl} (${confPctStr})`}
                />
                <CheckRow
                  label="SHA-256 Hash Integrity"
                  status="FAILED"
                  detail="Hash mismatch — file was modified"
                />
              </div>

              {result.reason ? (
                <p className="mt-3 text-sm text-amber-700/90 dark:text-amber-300/90">
                  {result.reason}
                </p>
              ) : null}
            </div>
          ) : null}

          {/* ── INVALID ─────────────────────────────────────────────────── */}
          {verdict === "INVALID" ? (
            <div className="rounded-xl border-2 border-destructive/50 bg-destructive/10 p-8 text-center">
              <div className="mb-3 flex justify-center">
                <AlertTriangle className="h-14 w-14 text-destructive" />
              </div>
              <p className="text-2xl font-extrabold tracking-tight text-destructive">
                INVALID
              </p>
              <p className="mt-2 text-sm text-muted-foreground">
                RSA digital signature validation failed.
              </p>

              {/* Check summary for invalid */}
              <div className="mt-4 border-t border-destructive/20 pt-4 space-y-1 text-left">
                <CheckRow
                  label="AI Forgery Detection"
                  status={checks?.ai_forgery_detection?.status ?? "PASSED"}
                  detail={`AI signal: ${fl} (${confPctStr})`}
                />
                <CheckRow
                  label="SHA-256 Hash Integrity"
                  status={checks?.hash_integrity?.status ?? "PASSED"}
                  detail="Hash matches"
                />
                <CheckRow
                  label="RSA Digital Signature"
                  status="FAILED"
                  detail="Signature could not be verified"
                />
              </div>

              {result.reason ? (
                <p className="mt-2 text-sm text-destructive/90">{result.reason}</p>
              ) : null}
            </div>
          ) : null}

        </div>
      ) : null}
    </form>
  );
}

interface VerificationRow {
  id: number;
  certificate_id: number;
  student_name: string;
  result: string;
  verified_at: string;
}

function VerifierHistory({ refreshKey }: { refreshKey: number }) {
  const [rows, setRows] = useState<VerificationRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setErr("");
      try {
        const { data } = await api.get<{ verifications: VerificationRow[] }>(
          "/verifications/my"
        );
        if (!cancelled) setRows(data.verifications ?? []);
      } catch (e: unknown) {
        if (!cancelled) setErr(formatApiError(e));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  return (
    <div className="mt-12 border-t border-border pt-10">
      <h2 className="text-lg font-semibold mb-4">Your verification history</h2>
      {err ? (
        <p className="text-sm text-destructive">{err}</p>
      ) : loading ? (
        <p className="text-sm text-muted-foreground">Loading…</p>
      ) : rows.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No verifications recorded yet. Upload a PDF on the tab above while logged in.
        </p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-border">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-secondary/40 text-left">
                <th className="p-3 font-medium">Certificate ID</th>
                <th className="p-3 font-medium">Student</th>
                <th className="p-3 font-medium">Result</th>
                <th className="p-3 font-medium">Date</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} className="border-b border-border/60 last:border-0">
                  <td className="p-3 font-mono">{r.certificate_id}</td>
                  <td className="p-3">{r.student_name}</td>
                  <td className="p-3">
                    <span
                      className={
                        r.result === "AUTHENTIC"
                          ? "text-success font-medium"
                          : "text-destructive font-medium"
                      }
                    >
                      {r.result}
                    </span>
                  </td>
                  <td className="p-3 text-muted-foreground">
                    {formatDisplayDate(r.verified_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default VerifyPage;