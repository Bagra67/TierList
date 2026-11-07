import { expect, type APIRequestContext } from '@playwright/test';

import { MAILPIT_API_URL } from './app.ts';

interface MailpitSearchResult {
  messages: { ID: string }[];
}

interface MailpitMessage {
  HTML: string;
}

async function latestMessageTo(
  request: APIRequestContext,
  address: string,
): Promise<MailpitMessage> {
  let messageId: string | undefined;
  await expect
    .poll(
      async () => {
        const response = await request.get(`${MAILPIT_API_URL}/search`, {
          params: { query: `to:"${address}"` },
        });
        const found: MailpitSearchResult = (await response.json()) as MailpitSearchResult;
        messageId = found.messages[0]?.ID;
        return messageId;
      },
      { message: `no email received by ${address}` },
    )
    .toBeDefined();
  const response = await request.get(`${MAILPIT_API_URL}/message/${messageId}`);
  return (await response.json()) as MailpitMessage;
}

export async function linkSentTo(
  request: APIRequestContext,
  address: string,
  path: string,
): Promise<string> {
  const message: MailpitMessage = await latestMessageTo(request, address);
  const link: string | undefined = message.HTML.match(/href="([^"]+)"/g)
    ?.map((attribute) => attribute.slice('href="'.length, -1).replaceAll('&amp;', '&'))
    .find((href) => new URL(href).pathname === path);
  if (link === undefined) throw new Error(`no ${path} link in the email sent to ${address}`);
  return link;
}
