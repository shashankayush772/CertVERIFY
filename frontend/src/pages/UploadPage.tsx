import { useState, useRef } from "react";
import { Link, Navigate } from "react-router-dom";
import { Upload, CheckCircle, Copy, Download, FileText } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import api, { formatApiError } from "@/lib/api";

interface IssueResponse {
  cert_id: number;
  id: number;
  qr_image_base64?: string;
  status?: string;
  student_name?: string;
  degree?: string;
  institution_name?: string;
  issue_date?: string;
  cert_hash?: string;
}

const UploadPage = () => {
  const { isLoggedIn, role } = useAuth();
  const [studentName, setStudentName] = useState("");
  const [degree, setDegree] = useState("");
  const [institution, setInstitution] = useState("");
  const [issueDate, setIssueDate] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<IssueResponse | null>(null);
  const [copied, setCopied] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isLoggedIn) {
    return <Navigate to="/login" replace />;
  }

  if (role !== "institution") {
    return (
      <div className="container max-w-lg py-16">
        <div className="glass-card p-8 text-center">
          <p className="text-muted-foreground">
            This page is for institutions only. Please log in with an institution account.
          </p>
          <Link
            to="/login"
            className="mt-6 inline-block rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90"
          >
            Go to login
          </Link>
        </div>
      </div>
    );
  }

  const ALLOWED_TYPES = ["application/pdf", "image/jpeg", "image/png"];

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped && ALLOWED_TYPES.includes(dropped.type)) setFile(dropped);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;
    setLoading(true);
    setError("");

    try {
      const issueIso = new Date(`${issueDate}T12:00:00`).toISOString();
      const formData = new FormData();
      formData.append("student_name", studentName);
      formData.append("degree", degree);
      formData.append("institution_name", institution);
      formData.append("issue_date", issueIso);
      formData.append("file", file);

      const { data } = await api.post<IssueResponse>("/certificates", formData);
      setResult(data);
    } catch (err: unknown) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  const copyId = () => {
    if (result) {
      const id = String(result.cert_id ?? result.id);
      void navigator.clipboard.writeText(id);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const certIdStr = result ? String(result.cert_id ?? result.id) : "";
  const qrB64 = result?.qr_image_base64 ?? "";

  if (result) {
    const issued =
      result.issue_date != null
        ? new Date(result.issue_date).toLocaleString()
        : "—";

    return (
      <div className="container flex min-h-[calc(100vh-4rem)] items-center justify-center py-12">
        <div className="animate-fade-up glass-card w-full max-w-lg p-8 border-success/30">
          <div className="mb-6 flex flex-col items-center text-center">
            <div className="mb-4 inline-flex h-14 w-14 items-center justify-center rounded-full bg-success/10">
              <CheckCircle className="h-7 w-7 text-success" />
            </div>
            <h2 className="text-2xl font-bold">Certificate Issued!</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              The certificate has been securely registered.
            </p>
          </div>

          <div className="space-y-4">
            <div>
              <label className="mb-1.5 block text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Certificate ID
              </label>
              <div className="flex items-center gap-2">
                <code className="flex-1 rounded-lg border border-input bg-background/50 px-4 py-2.5 text-sm font-mono">
                  {certIdStr}
                </code>
                <button
                  type="button"
                  onClick={copyId}
                  className="rounded-lg border border-input p-2.5 hover:bg-secondary transition-colors active:scale-95"
                >
                  <Copy className="h-4 w-4" />
                </button>
              </div>
              {copied && (
                <p className="mt-1 text-xs text-success">Copied to clipboard!</p>
              )}
            </div>

            <div className="rounded-lg border border-border/50 bg-background/30 p-4 text-sm space-y-2">
              <p>
                <span className="text-muted-foreground">Student: </span>
                <span className="font-medium">{result.student_name ?? "—"}</span>
              </p>
              <p>
                <span className="text-muted-foreground">Degree: </span>
                <span className="font-medium">{result.degree ?? "—"}</span>
              </p>
              <p>
                <span className="text-muted-foreground">Institution: </span>
                <span className="font-medium">{result.institution_name ?? "—"}</span>
              </p>
              <p>
                <span className="text-muted-foreground">Issue date: </span>
                <span className="font-medium">{issued}</span>
              </p>
              <p>
                <span className="text-muted-foreground">Status: </span>
                <span className="font-medium">{result.status ?? "—"}</span>
              </p>
              <p className="break-all">
                <span className="text-muted-foreground">SHA-256: </span>
                <span className="font-mono text-xs">{result.cert_hash ?? "—"}</span>
              </p>
            </div>

            {qrB64 ? (
              <div className="flex flex-col items-center gap-3 pt-2">
                <img
                  src={`data:image/png;base64,${qrB64}`}
                  alt="Certificate QR Code"
                  className="h-48 w-48 rounded-lg border border-border bg-foreground p-2"
                />
                <a
                  href={`data:image/png;base64,${qrB64}`}
                  download={`cert-${certIdStr}-qr.png`}
                  className="inline-flex items-center gap-2 rounded-lg border border-input px-4 py-2 text-sm font-medium hover:bg-secondary transition-colors active:scale-95"
                >
                  <Download className="h-4 w-4" />
                  Download QR Code
                </a>
              </div>
            ) : null}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="container max-w-2xl py-12">
      <div className="animate-fade-up mb-8">
        <h1 className="text-3xl font-bold">Issue New Certificate</h1>
        <p className="mt-2 text-muted-foreground">
          Fill in the details and upload the certificate (PDF, JPG, or PNG).
        </p>
      </div>

      {error ? (
        <div className="mb-6 rounded-lg bg-destructive/10 border border-destructive/20 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      ) : null}

      <form onSubmit={handleSubmit} className="animate-fade-up-delay-1 space-y-6">
        <div className="glass-card p-6 space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="mb-1.5 block text-sm font-medium">Student Name</label>
              <input
                required
                value={studentName}
                onChange={(e) => setStudentName(e.target.value)}
                placeholder="Full name"
                className="w-full rounded-lg border border-input bg-background/50 px-4 py-2.5 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring transition-shadow"
              />
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-medium">Degree</label>
              <input
                required
                value={degree}
                onChange={(e) => setDegree(e.target.value)}
                placeholder="e.g., Bachelor of Science"
                className="w-full rounded-lg border border-input bg-background/50 px-4 py-2.5 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring transition-shadow"
              />
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="mb-1.5 block text-sm font-medium">Institution Name</label>
              <input
                required
                value={institution}
                onChange={(e) => setInstitution(e.target.value)}
                placeholder="University name"
                className="w-full rounded-lg border border-input bg-background/50 px-4 py-2.5 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring transition-shadow"
              />
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-medium">Issue Date</label>
              <input
                type="date"
                required
                value={issueDate}
                onChange={(e) => setIssueDate(e.target.value)}
                className="w-full rounded-lg border border-input bg-background/50 px-4 py-2.5 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring transition-shadow"
              />
            </div>
          </div>
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
              <p className="text-xs text-muted-foreground">Click to change file</p>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-2">
              <Upload className="h-10 w-10 text-muted-foreground" />
              <p className="text-sm font-medium">
                Drag & drop your certificate here
              </p>
              <p className="text-xs text-muted-foreground">
                PDF, JPG, or PNG — click to browse
              </p>
            </div>
          )}
        </div>

        <button
          type="submit"
          disabled={loading || !file}
          className="w-full rounded-lg bg-primary px-4 py-3 text-sm font-semibold text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors active:scale-[0.98]"
        >
          {loading ? "Issuing Certificate..." : "Issue Certificate"}
        </button>
      </form>
    </div>
  );
};

export default UploadPage;
