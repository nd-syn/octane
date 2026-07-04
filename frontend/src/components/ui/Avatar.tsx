interface Props {
  name: string;
  size?: 'small' | 'medium' | 'default';
}

export function Avatar({ name, size = 'default' }: Props) {
  const letter = name ? name[0].toUpperCase() : '?';
  return <div className={`avatar ${size !== 'default' ? size : ''}`}>{letter}</div>;
}
