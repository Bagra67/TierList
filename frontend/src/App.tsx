import { useHello } from './api/hello';

export default function App() {
  const { data: hello, isPending, isError } = useHello();

  if (isPending) return <p>Chargement…</p>;
  if (isError) return <p role="alert">Impossible de joindre le backend : est-il lancé ?</p>;
  return <h1>{hello.message}</h1>;
}
