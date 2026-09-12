"use client";

import { useEffect, useRef } from "react";

/** Content stays readable before hydration and if animation cannot load. */
export function ScrollReveal({ children, className }: {
  children: React.ReactNode;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const element = ref.current;
    if (!element || !("IntersectionObserver" in window)) return;
    const preference = window.matchMedia("(prefers-reduced-motion: reduce)");
    const animations: Animation[] = [];
    const observer = new IntersectionObserver(([entry]) => {
      if (!entry.isIntersecting) return;
      observer.disconnect();
      if (preference.matches) return;
      Array.from(element.children).forEach((child, index) => {
        animations.push(child.animate(
          [{ opacity: 0, transform: "translateY(16px)" }, { opacity: 1, transform: "translateY(0)" }],
          { duration: 480, delay: Math.min(index * 70, 280), easing: "cubic-bezier(0.22, 1, 0.36, 1)", fill: "backwards" },
        ));
      });
    }, { rootMargin: "0px 0px -8% 0px" });
    const stop = () => { if (preference.matches) animations.forEach((animation) => animation.cancel()); };
    observer.observe(element);
    preference.addEventListener("change", stop);
    return () => {
      observer.disconnect();
      preference.removeEventListener("change", stop);
      animations.forEach((animation) => animation.cancel());
    };
  }, []);

  return <div ref={ref} className={className}>{children}</div>;
}
