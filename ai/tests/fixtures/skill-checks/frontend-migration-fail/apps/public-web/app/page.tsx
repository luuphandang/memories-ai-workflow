export function LegacyPage() {
  document.querySelector('#menu');
  return <div dangerouslySetInnerHTML={{ __html: '<button onclick="open()">Open</button>' }} />;
}
