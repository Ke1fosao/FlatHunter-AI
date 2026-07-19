import Link from "next/link";

export default function NotFound() {
  return (
    <main className="route-page">
      <section className="page-state page-state--empty">
        <span className="page-state__icon" aria-hidden="true">
          404
        </span>
        <h1>Сторінку не знайдено</h1>
        <p>Посилання застаріло або такого розділу не існує.</p>
        <div className="page-state__action">
          <Link href="/search">Повернутися до пошуку</Link>
        </div>
      </section>
    </main>
  );
}
