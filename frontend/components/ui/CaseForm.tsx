
"use client";
import { useState } from "react";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent } from "@/components/ui/card";
import toast from "react-hot-toast";

export default function CaseForm() {
  const [form, setForm] = useState({
    radiology: "",
    ecg: "",
    symptoms_text: "",
    lab_text: ""
  });
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  const handleSubmit = async () => {
    setLoading(true);
    try {
      const res = await api.post("/diagnose", form);
      setResult(res.data);
      toast.success("Diagnosis complete");
    } catch (e: any) {
      toast.error("Error: " + e.message);
    }
    setLoading(false);
  };

  return (
    <Card className="p-6 w-full max-w-2xl mx-auto">
      <CardContent className="space-y-4">
        {["radiology","ecg","symptoms_text","lab_text"].map((key) => (
          <Textarea
            key={key}
            placeholder={key.replace("_"," ").toUpperCase()}
            value={form[key as keyof typeof form]}
            onChange={(e) => setForm({...form, [key]: e.target.value})}
          />
        ))}
        <Button onClick={handleSubmit} disabled={loading}>
          {loading ? "Analyzing..." : "Run Diagnosis"}
        </Button>

        {result && (
          <pre className="bg-gray-900 text-green-400 p-3 mt-4 rounded-md text-sm overflow-auto max-h-[300px]">
            {JSON.stringify(result, null, 2)}
          </pre>
        )}
      </CardContent>
    </Card>
  );
}
