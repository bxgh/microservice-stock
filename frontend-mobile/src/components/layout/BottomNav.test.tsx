import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import BottomNav from './BottomNav';
import { describe, it, expect } from 'vitest';

describe('BottomNav', () => {
    it('renders all navigation tabs', () => {
        render(
            <BrowserRouter>
                <BottomNav />
            </BrowserRouter>
        );

        expect(screen.getByText('Dashboard')).toBeInTheDocument();
        expect(screen.getByText('Screener')).toBeInTheDocument();
        expect(screen.getByText('Console')).toBeInTheDocument();
    });
});
