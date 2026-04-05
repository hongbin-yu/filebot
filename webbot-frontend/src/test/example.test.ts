import { describe, it, expect } from 'vitest';

describe('Test infrastructure verification', () => {
  it('should run basic test', () => {
    expect(1 + 1).toBe(2);
  });

  it('should have DOM available', () => {
    const div = document.createElement('div');
    div.textContent = 'Hello, World!';
    document.body.appendChild(div);

    expect(document.body.innerHTML).toContain('Hello, World!');
  });

  it('should have testing-library matchers available', () => {
    const element = document.createElement('div');
    element.setAttribute('data-testid', 'test-element');
    document.body.appendChild(element);

    expect(element).toBeInTheDocument();
  });
});
