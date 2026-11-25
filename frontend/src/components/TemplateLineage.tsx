import { Fragment } from 'react';
import { type UseTranslationResponse, useTranslation } from 'react-i18next';
import { Link } from 'react-router';

import type { LineageAncestor } from '../api/marketplace';
import { publicTemplatePath } from '../constants/routes';
import { textLinkClassName } from './ui/text-link';

function AncestorName({ ancestor }: { ancestor: LineageAncestor }) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  const quoted: string = t('lineage.name', { name: ancestor.name });
  if (ancestor.template_id === null) return <span className="text-foreground">{quoted}</span>;
  return (
    <Link to={publicTemplatePath(ancestor.template_id)} className={textLinkClassName}>
      {quoted}
    </Link>
  );
}

function AncestorOwner({ ancestor }: { ancestor: LineageAncestor }) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  if (ancestor.owner_name === null) return null;
  return <> {t('lineage.byOwner', { owner: ancestor.owner_name })}</>;
}

export function TemplateLineage({ lineage }: { lineage: LineageAncestor[] }) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  return (
    <span>
      {lineage.map((ancestor: LineageAncestor, index: number) => (
        <Fragment key={`${index}-${ancestor.name}`}>
          {index === 0 ? t('lineage.copiedFrom') : t('lineage.itselfCopiedFrom')}{' '}
          <AncestorName ancestor={ancestor} />
          <AncestorOwner ancestor={ancestor} />
        </Fragment>
      ))}
    </span>
  );
}

export function CopiedFrom({ ancestor }: { ancestor: LineageAncestor }) {
  return <TemplateLineage lineage={[ancestor]} />;
}
