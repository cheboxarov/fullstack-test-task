import { Form } from "react-bootstrap";

interface PageSizeSelectProps {
  value: number;
  onChange: (pageSize: number) => void;
  options?: number[];
}

export function PageSizeSelect({ 
  value, 
  onChange, 
  options = [10, 25, 50] 
}: PageSizeSelectProps) {
  return (
    <Form.Select
      size="sm"
      value={value}
      onChange={(e) => onChange(Number(e.target.value))}
      style={{ width: "auto" }}
    >
      {options.map((size) => (
        <option key={size} value={size}>
          {size} на странице
        </option>
      ))}
    </Form.Select>
  );
}
