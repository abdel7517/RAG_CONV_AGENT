import ChatWidget from "~/app/components/ChatWidget";
import { DemoEcommerceWebsite } from "~/app/components/DemoEcommerceWebsite";

interface HomeProps {
  token: string | null
  companyId: string
}

export default function Home({ token, companyId }: HomeProps) {

  return (
    <>
      <DemoEcommerceWebsite />
      {token && companyId ? (
        <ChatWidget token={token} companyId={companyId} />
      ) : (
        <div className="fixed bottom-6 right-6 z-50 bg-red-500 text-white p-4 rounded">
          Token manquant - Backend down?
        </div>
      )}
    </>
  )
}
