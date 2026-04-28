/**
 * Delivery placeholder.
 *
 * Future use:
 *   - Email the written digest + MP3 attachment / link at 6:30 AM PT
 *   - Push notification with "Today's briefing is ready"
 *   - Optional: private podcast feed (RSS) so audio briefing is in podcast apps
 */

export interface DeliveryPayload {
  email: string;
  digestHtml: string;
  audioUrl: string;
}

export async function deliverMorning(_payload: DeliveryPayload): Promise<void> {
  // TODO(integration): hand off to backend mailer (Resend/Postmark/SES) on a cron.
}
