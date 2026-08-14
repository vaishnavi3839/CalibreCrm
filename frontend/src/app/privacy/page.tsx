"use client";

export default function PrivacyPage() {
  return (
    <main className="mx-auto max-w-2xl px-4 py-12 text-navy-900">
      <h1 className="text-2xl font-semibold">Privacy Policy</h1>
      <p className="mt-2 text-sm text-muted">Calibre Aviation Academy CRM</p>
      <div className="mt-6 space-y-4 text-sm leading-relaxed text-navy-800">
        <p>
          This app is used by academy staff, students, and parents for CRM, attendance, and academic
          operations.
        </p>
        <p>
          <strong>Data we collect:</strong> account email and name; attendance punch time; branch GPS
          location at punch; selfie photos for grooming checks; lead/CRM notes entered by staff.
        </p>
        <p>
          <strong>How we use it:</strong> mark attendance, enforce academy grooming and late rules,
          calculate salary deductions, notify parents of student arrival/late events, and manage leads.
        </p>
        <p>
          <strong>Sharing:</strong> data stays within the academy system. We do not sell personal data.
        </p>
        <p>
          <strong>Contact:</strong> for access or deletion requests, email your academy administrator.
        </p>
      </div>
    </main>
  );
}
