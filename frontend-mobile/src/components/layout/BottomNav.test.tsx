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

        expect(screen.getByText('首页')).toBeInTheDocument();
        expect(screen.getByText('选股')).toBeInTheDocument();
        expect(screen.getByText('行情')).toBeInTheDocument();
        expect(screen.getByText('管理')).toBeInTheDocument();
    });
});
