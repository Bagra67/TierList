import { useEffect, useState } from 'react';

import { getHello } from './api/hello';

export default function App() {
  const [message, setMessage] = useState<string | null>(null);
  const [hasError, setHasError] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    getHello(controller.signal)
      .then((hello) => setMessage(hello.message))
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          console.error('Échec de GET /api/hello', error);
          setHasError(true);
        }
      });
    return () => controller.abort();
  }, []);

  if (hasError) return <p role="alert">Impossible de joindre le backend : est-il lancé ?</p>;
  if (message === null) return <p>Chargement…</p>;
  return <h1>{message}</h1>;
}
