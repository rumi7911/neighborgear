import { useEffect, useRef, type ReactNode } from "react";
import { X } from "lucide-react";
export const label = (s: string | undefined) =>
  s
    ? s.replaceAll("_", " ").replace(/^./, (x) => x.toUpperCase())
    : "Not specified";
export const date = (s: string | undefined) =>
  s
    ? new Date(s.slice(0, 10) + "T12:00:00Z").toLocaleDateString("en-GB", {
        day: "numeric",
        month: "short",
      })
    : "Not set";
export const initials = (s: string) =>
  s
    .replace(/\([^)]*\)/g, "")
    .trim()
    .split(/\s+/)
    .map((n) => n[0])
    .slice(0, 2)
    .join("");
export function Status({ value }: { value: string }) {
  return <span className={`status status-${value}`}>{label(value)}</span>;
}
export function Modal({
  title,
  children,
  onClose,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    ref.current?.showModal();
    const old = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = old;
    };
  }, []);
  return (
    <dialog
      ref={ref}
      onCancel={onClose}
      onClick={(e) => {
        if (e.target === ref.current) onClose();
      }}
      aria-labelledby="dialog-title"
    >
      <div className="modal-head">
        <h2 id="dialog-title">{title}</h2>
        <button
          className="icon-button"
          onClick={onClose}
          aria-label="Close dialog"
        >
          <X size={20} />
        </button>
      </div>
      {children}
    </dialog>
  );
}
export function Empty({ children }: { children: ReactNode }) {
  return <div className="empty">{children}</div>;
}
