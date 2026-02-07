import { ShieldAlert } from 'lucide-react';
import { useI18n } from '../context/I18nContext';

export default function AlertBanner() {
  const { t } = useI18n();
  const message = t('alertBanner.message');

  // Double the message for seamless loop
  const repeatedMessage = message.repeat(4);

  return (
    <div className="neo-alert-banner">
      <div className="relative flex overflow-hidden">
        <div className="neo-alert-text flex items-center gap-3">
          <ShieldAlert className="w-5 h-5 inline-block" />
          {repeatedMessage}
        </div>
      </div>
    </div>
  );
}

