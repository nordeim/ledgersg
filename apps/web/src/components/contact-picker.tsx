"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Loader2, Search, X } from "lucide-react";
import { Input } from "@/components/ui/input";
import { useContacts, type Contact } from "@/hooks/use-contacts";

/**
 * P9/B-3: a searchable contact picker — the Receive/Make payment forms
 * previously bound `contact_id` to a raw text input (UUID-validated), so a
 * user could not select a customer at all (no contacts page exists; the
 * UUID is unknowable through the UI).
 *
 * Debounced server-side search through the real list endpoint
 * (?search=&is_customer= / ?search=&is_supplier=); the selected contact's
 * id flows to the form via onChange.
 */

interface ContactPickerProps {
  orgId: string;
  type: "customer" | "supplier";
  value: string;
  onChange: (contactId: string) => void;
  /** P10/H-1: optional full-contact callback — the invoice form mirrors
   * the picked contact's name into its own form state (its zod schema
   * requires customer.name) without re-fetching the row. */
  onSelect?: (contact: Contact) => void;
  disabled?: boolean;
  invalid?: boolean;
}

export function ContactPicker({
  orgId,
  type,
  value,
  onChange,
  onSelect,
  disabled = false,
  invalid = false,
}: ContactPickerProps) {
  const [query, setQuery] = useState("");
  const [debounced, setDebounced] = useState("");
  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState<Contact | null>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);

  // Debounce the search so typing doesn't hammer the endpoint per keystroke.
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(query.trim()), 300);
    return () => clearTimeout(timer);
  }, [query]);

  useEffect(() => {
    const onClickAway = (e: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onClickAway);
    return () => document.removeEventListener("mousedown", onClickAway);
  }, []);

  const { data: contacts, isLoading } = useContacts(orgId, {
    search: debounced || undefined,
    ...(type === "customer" ? { is_customer: true } : { is_supplier: true }),
    is_active: true,
  });

  const results = useMemo(() => contacts ?? [], [contacts]);

  // A controlled value (e.g. a prefilled deep link, P9/B-3b) must display
  // its contact even before the user searches: derive it from the loaded
  // list when no explicit selection has been made.
  const effectiveSelected = useMemo(
    () => selected ?? results.find((c) => c.id === value) ?? null,
    [selected, results, value]
  );

  const handleSelect = (contact: Contact) => {
    setSelected(contact);
    onChange(contact.id);
    onSelect?.(contact);
    setOpen(false);
    setQuery("");
  };

  const handleClear = () => {
    setSelected(null);
    onChange("");
    setQuery("");
  };

  return (
    <div ref={wrapperRef} className="relative">
      {effectiveSelected ? (
        <div className="flex items-center justify-between h-10 w-full rounded-sm border border-border bg-surface px-3 py-2">
          <div className="text-sm text-text-primary truncate">
            <span className="font-medium">{effectiveSelected.name}</span>
            {effectiveSelected.email ? (
              <span className="text-text-muted"> · {effectiveSelected.email}</span>
            ) : null}
          </div>
          {!disabled && (
            <button
              type="button"
              onClick={handleClear}
              aria-label={`Clear ${type}`}
              className="text-text-muted hover:text-text-primary"
            >
              <X className="h-4 w-4" aria-hidden />
            </button>
          )}
        </div>
      ) : (
        <>
          <div className="relative">
            <Search
              className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-text-muted"
              aria-hidden
            />
            <Input
              placeholder={`Search ${type}s by name…`}
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setOpen(true);
              }}
              onFocus={() => setOpen(true)}
              disabled={disabled}
              aria-invalid={invalid}
              className="rounded-sm pl-9"
              role="combobox"
              aria-expanded={open}
              aria-label={`Search ${type}`}
            />
            {isLoading && (
              <Loader2
                className="h-4 w-4 absolute right-3 top-1/2 -translate-y-1/2 animate-spin text-text-muted"
                aria-hidden
              />
            )}
          </div>
          {open && (
            <ul
              role="listbox"
              aria-label={`${type} results`}
              className="absolute z-20 left-0 right-0 mt-1 max-h-56 overflow-auto rounded-sm border border-border bg-carbon shadow-lg"
            >
              {results.length === 0 ? (
                <li className="px-3 py-3 text-sm text-text-secondary">
                  {debounced
                    ? `No ${type}s match “${debounced}”.`
                    : `Start typing to search your ${type}s.`}
                </li>
              ) : (
                results.map((contact) => (
                  <li key={contact.id}>
                    <button
                      type="button"
                      role="option"
                      aria-selected={false}
                      onClick={() => handleSelect(contact)}
                      className="w-full text-left px-3 py-2 text-sm text-text-primary hover:bg-surface transition-colors"
                    >
                      <span className="font-medium">{contact.name}</span>
                      {contact.email ? (
                        <span className="text-text-muted"> · {contact.email}</span>
                      ) : null}
                    </button>
                  </li>
                ))
              )}
            </ul>
          )}
        </>
      )}
    </div>
  );
}
