"use client";

import { useMemo, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Loader2, Pencil, Search, UserX, Users } from "lucide-react";
import { useAuth } from "@/providers/auth-provider";
import { toast } from "@/hooks/use-toast";
import {
  useContacts,
  useUpdateContact,
  useDeactivateContact,
  type Contact,
} from "@/hooks/use-contacts";

/**
 * P10/M-5 — the contacts management surface. The backend has full CRUD
 * (list w/ filters, create, GET/PATCH/DELETE-deactivate) and the hooks
 * existed, but no page did: a wrong Peppol ID or email (required for
 * InvoiceNow sends) could never be corrected in-app.
 *
 * List with server-side search (the backend's real filter keys) + type
 * filter; Edit (PATCH allowlist fields); Deactivate (confirm-gated).
 */

type TypeFilter = "all" | "customers" | "suppliers";

export default function ContactsClient() {
  const { currentOrg } = useAuth();
  const orgId = currentOrg?.id ?? "";

  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState<TypeFilter>("all");
  const [editing, setEditing] = useState<Contact | null>(null);
  const [deactivating, setDeactivating] = useState<Contact | null>(null);

  // Debounce the search so typing doesn't hammer the endpoint per keystroke.
  useMemo(() => {
    const timer = setTimeout(() => setDebouncedSearch(search.trim()), 300);
    return () => clearTimeout(timer);
  }, [search]);

  const filters = useMemo(() => {
    const base: Record<string, boolean | string> = {};
    if (debouncedSearch) base.search = debouncedSearch;
    if (typeFilter === "customers") base.is_customer = true;
    if (typeFilter === "suppliers") base.is_supplier = true;
    return base;
  }, [debouncedSearch, typeFilter]);

  const { data: contacts, isLoading, isError } = useContacts(orgId, filters);

  return (
    <div className="space-y-4" data-testid="contacts-client">
      {/* Toolbar */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1 max-w-sm">
          <Search
            className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-text-muted"
            aria-hidden
          />
          <Input
            aria-label="Search contacts"
            placeholder="Search by name, email or UEN…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="rounded-sm pl-9"
          />
        </div>
        <div className="flex gap-1 rounded-sm border border-border p-1" role="group" aria-label="Filter by type">
          {(["all", "customers", "suppliers"] as const).map((t) => (
            <Button
              key={t}
              type="button"
              variant="ghost"
              size="sm"
              aria-pressed={typeFilter === t}
              className={
                typeFilter === t
                  ? "rounded-sm bg-surface text-accent-primary h-8"
                  : "rounded-sm text-text-secondary h-8"
              }
              onClick={() => setTypeFilter(t)}
            >
              {t === "all" ? "All" : t === "customers" ? "Customers only" : "Suppliers only"}
            </Button>
          ))}
        </div>
      </div>

      {/* List */}
      {isLoading ? (
        <div className="flex items-center gap-2 text-sm text-text-secondary py-12 justify-center">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
          Loading contacts…
        </div>
      ) : isError ? (
        <Card className="border-border bg-carbon rounded-sm">
          <CardContent className="py-12 text-center text-sm text-alert">
            Failed to load contacts. Please try again.
          </CardContent>
        </Card>
      ) : !contacts || contacts.length === 0 ? (
        <Card className="border-border bg-carbon rounded-sm">
          <CardContent className="py-12 text-center space-y-2">
            <Users className="h-8 w-8 mx-auto text-text-muted" aria-hidden />
            <p className="text-sm text-text-secondary">No contacts yet.</p>
            <p className="text-xs text-text-muted">
              Contacts are created when you invoice a new customer (or add one
              in the payment forms) — manage them here.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-2" data-testid="contacts-list">
          {contacts.map((contact) => (
            <ContactRow
              key={contact.id}
              contact={contact}
              onEdit={() => setEditing(contact)}
              onDeactivate={() => setDeactivating(contact)}
            />
          ))}
        </div>
      )}

      {/* Edit dialog */}
      {editing && (
        <EditContactDialog
          orgId={orgId}
          contact={editing}
          open={!!editing}
          onOpenChange={(open) => !open && setEditing(null)}
        />
      )}

      {/* Deactivate confirm (the void-reason dialog pattern) */}
      <Dialog open={!!deactivating} onOpenChange={(open) => !open && setDeactivating(null)}>
        <DialogContent className="border-border bg-carbon rounded-sm max-w-md">
          <DialogHeader>
            <DialogTitle className="font-display text-xl text-text-primary">
              Deactivate contact
            </DialogTitle>
            <DialogDescription>
              Deactivate this contact? {deactivating?.name} will no longer be
              selectable in pickers; existing documents keep their history.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              className="rounded-sm border-border"
              onClick={() => setDeactivating(null)}
            >
              Cancel
            </Button>
            <DeactivateButton
              orgId={orgId}
              contactId={deactivating?.id ?? ""}
              onDone={() => setDeactivating(null)}
            />
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function ContactRow({
  contact,
  onEdit,
  onDeactivate,
}: {
  contact: Contact;
  onEdit: () => void;
  onDeactivate: () => void;
}) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-sm border border-border bg-carbon p-4">
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm font-medium text-text-primary truncate">
            {contact.name}
          </span>
          <Badge variant="outline" className="rounded-sm text-xs">
            {contact.contact_type === "BOTH"
              ? "Customer + Supplier"
              : contact.contact_type === "SUPPLIER"
                ? "Supplier"
                : "Customer"}
          </Badge>
          {!contact.is_active && (
            <Badge variant="outline" className="rounded-sm text-xs text-text-muted">
              Inactive
            </Badge>
          )}
          {contact.is_peppol_enabled && (
            <Badge variant="outline" className="rounded-sm text-xs text-accent-primary">
              Peppol
            </Badge>
          )}
        </div>
        <div className="text-xs text-text-secondary mt-1 flex flex-wrap gap-x-3">
          {contact.email && <span>{contact.email}</span>}
          {contact.uen && <span>UEN {contact.uen}</span>}
          {contact.peppol_id && <span>Peppol ID {contact.peppol_id}</span>}
        </div>
      </div>
      <div className="flex gap-1 shrink-0">
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="rounded-sm border-border h-8"
          aria-label={`Edit ${contact.name}`}
          onClick={onEdit}
        >
          <Pencil className="h-3.5 w-3.5" aria-hidden />
          Edit
        </Button>
        {contact.is_active && (
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="rounded-sm border-border h-8 text-alert hover:text-alert"
            aria-label={`Deactivate ${contact.name}`}
            onClick={onDeactivate}
          >
            <UserX className="h-3.5 w-3.5" aria-hidden />
            Deactivate
          </Button>
        )}
      </div>
    </div>
  );
}

function DeactivateButton({
  orgId,
  contactId,
  onDone,
}: {
  orgId: string;
  contactId: string;
  onDone: () => void;
}) {
  const deactivate = useDeactivateContact(orgId, contactId);
  return (
    <Button
      type="button"
      className="rounded-sm bg-alert text-white hover:bg-alert/90"
      disabled={deactivate.isPending}
      onClick={() => {
        deactivate.mutateAsync().then(onDone).catch((err) => {
          toast({
            title: "Deactivate failed",
            description: err instanceof Error ? err.message : "Please try again.",
            variant: "error",
          });
        });
      }}
    >
      {deactivate.isPending ? (
        <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
      ) : (
        "Deactivate"
      )}
    </Button>
  );
}

const EDIT_FIELDS = [
  { key: "name", label: "Name", type: "text" },
  { key: "email", label: "Email", type: "email" },
  { key: "phone", label: "Phone", type: "tel" },
  { key: "uen", label: "UEN", type: "text" },
  { key: "gst_reg_number", label: "GST Registration No", type: "text" },
  { key: "peppol_id", label: "Peppol ID", type: "text" },
  { key: "address_line_1", label: "Address Line 1", type: "text" },
  { key: "postal_code", label: "Postal Code", type: "text" },
] as const;

function EditContactDialog({
  orgId,
  contact,
  open,
  onOpenChange,
}: {
  orgId: string;
  contact: Contact;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const update = useUpdateContact(orgId, contact.id);
  const [form, setForm] = useState<Record<string, string>>(() =>
    Object.fromEntries(
      EDIT_FIELDS.map(({ key }) => [key, (contact as unknown as Record<string, string>)[key] ?? ""])
    )
  );
  const [error, setError] = useState<string | null>(null);

  const handleSave = async () => {
    setError(null);
    try {
      await update.mutateAsync(form as Parameters<typeof update.mutateAsync>[0]);
      toast({ title: "Contact updated", description: contact.name });
      onOpenChange(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save. Please try again.");
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="border-border bg-carbon rounded-sm max-w-lg">
        <DialogHeader>
          <DialogTitle className="font-display text-xl text-text-primary">
            Edit contact
          </DialogTitle>
          <DialogDescription>
            Correct the details — the Peppol ID is what InvoiceNow transmissions
            address.
          </DialogDescription>
        </DialogHeader>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {EDIT_FIELDS.map(({ key, label, type }) => (
            <Input
              key={key}
              label={label}
              type={type}
              value={form[key]}
              onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
              disabled={update.isPending}
            />
          ))}
        </div>
        {error && (
          <p className="text-sm text-alert" role="alert">
            {error}
          </p>
        )}
        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            className="rounded-sm border-border"
            onClick={() => onOpenChange(false)}
            disabled={update.isPending}
          >
            Cancel
          </Button>
          <Button
            type="button"
            className="rounded-sm bg-accent-primary text-void hover:bg-accent-primary-dim"
            onClick={handleSave}
            disabled={update.isPending}
          >
            {update.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
            ) : (
              "Save Changes"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
