import "./globals.css";

export const metadata={
  title:"CareerCoach AI — Adaptive Interview Coach",
  description:"Practice resume-aware, adaptive AI interviews with voice coaching and actionable feedback.",
};

export default function RootLayout({children}:{children:React.ReactNode}){
  return <html lang="en"><body>{children}</body></html>;
}
