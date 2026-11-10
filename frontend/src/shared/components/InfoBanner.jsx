const VARIANTS = {
  // Neutral/informational notices -- blue, matches the system's "positive" color.
  info: 'bg-primary-fixed text-on-primary-fixed-variant border-primary-container/40',
  // Caution -- amber. The design system never uses red for this.
  warning: 'bg-tertiary-fixed text-on-tertiary-fixed-variant border-tertiary-container/40',
}

/** @param {{children: any, variant?: 'info'|'warning'}} props */
export default function InfoBanner({ children, variant = 'info' }) {
  return (
    <div className={`border text-body-md rounded-lg p-3 ${VARIANTS[variant]}`}>
      {children}
    </div>
  )
}