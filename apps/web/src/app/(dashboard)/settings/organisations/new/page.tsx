import { NewOrganisationClient } from "./new-organisation-client";

/**
 * P9/O-1: the organisation-creation route — the target of the dashboard's
 * "Create Organisation" CTA (previously a 404 dead end; the backend's
 * POST /api/v1/organisations/ had zero frontend consumers).
 */
export default function NewOrganisationPage() {
  return <NewOrganisationClient />;
}
