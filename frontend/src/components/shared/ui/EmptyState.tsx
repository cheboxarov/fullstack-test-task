interface EmptyStateProps {
  message: string;
  colSpan: number;
}

export function EmptyState({ message, colSpan }: EmptyStateProps) {
  return (
    <tr>
      <td colSpan={colSpan} className="text-center py-4 text-secondary">
        {message}
      </td>
    </tr>
  );
}
