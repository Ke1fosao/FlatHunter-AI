"use client";

import { useEffect, useState } from "react";

import { setClusterState } from "@/lib/cluster-api";

type Props = {
  clusterId: string;
  initialNote: string;
  onSaved?: (note: string) => void;
};

export function ClusterNoteEditor({ clusterId, initialNote, onSaved }: Props) {
  const [note, setNote] = useState(initialNote);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    setNote(initialNote);
    setMessage("");
    setError("");
  }, [clusterId, initialNote]);

  const save = async () => {
    setBusy(true);
    setMessage("");
    setError("");
    try {
      const updated = await setClusterState(clusterId, { note });
      const savedNote = updated.user_state.note;
      setNote(savedNote);
      setMessage("Нотатку збережено");
      onSaved?.(savedNote);
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "Не вдалося зберегти нотатку.",
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="cluster-note-editor">
      <label>
        Ваша нотатка
        <textarea
          value={note}
          maxLength={500}
          placeholder="Що уточнити у власника або перевірити на перегляді?"
          onChange={(event) => setNote(event.target.value)}
        />
      </label>
      <div>
        <small>{note.length}/500</small>
        <button type="button" disabled={busy} onClick={() => void save()}>
          {busy ? "Зберігаю…" : "Зберегти нотатку"}
        </button>
      </div>
      {message && <p className="is-success">{message}</p>}
      {error && (
        <p className="is-error" role="status">
          {error}
        </p>
      )}
      <style jsx>{`
        .cluster-note-editor {
          display: grid;
          gap: 9px;
          padding: 16px;
          border: 1px solid var(--line);
          border-radius: 17px;
          background: var(--bg);
        }
        label {
          display: grid;
          gap: 7px;
          color: var(--muted);
          font-size: 11px;
          font-weight: 850;
        }
        textarea {
          min-height: 105px;
          border: 1px solid var(--line);
          border-radius: 13px;
          padding: 11px;
          background: var(--surface-solid);
          color: var(--text);
          font: inherit;
          line-height: 1.5;
          resize: vertical;
        }
        div {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
        }
        small {
          color: var(--muted);
        }
        button {
          min-height: 42px;
          border: 0;
          border-radius: 11px;
          padding: 0 14px;
          background: var(--accent);
          color: var(--accent-text);
          font-weight: 850;
          cursor: pointer;
        }
        button:disabled {
          opacity: 0.55;
        }
        p {
          margin: 0;
          font-size: 12px;
          font-weight: 750;
        }
        .is-success {
          color: var(--accent);
        }
        .is-error {
          color: var(--danger);
        }
      `}</style>
    </section>
  );
}
