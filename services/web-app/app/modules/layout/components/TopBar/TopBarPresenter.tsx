import React from 'react';
import { useAuth } from '@clients/api/modules/phantom-token-handler-secured-api-client/AuthContext';
import { startLogin, logout } from '@clients/api/client';
import { ErrorRenderer } from '@clients/api/modules/phantom-token-handler-secured-api-client/utilities/errorRenderer';
import { TopBarView } from './TopBarView';

export function TopBar() {
    const { isLoggedIn, userInfo, onLoggedOut } = useAuth();
    const [initials, setInitials] = React.useState('');

    // For initials:
    React.useEffect(() => {
        if (userInfo) {
            if (userInfo.name.givenName && userInfo.name.familyName) {
                const first = userInfo.name.givenName.charAt(0).toUpperCase();
                const last = userInfo.name.familyName.charAt(0).toUpperCase();
                setInitials(`${first}${last}`);
            } else if (userInfo.sub) {
                setInitials(userInfo.sub.substring(0, 2).toUpperCase());
            } else {
                setInitials('??');
            }
        }
    }, [userInfo]);

    async function handleLogin() {
        try {
            const response = await startLogin();
            window.location.href = response.authorizationUrl;
        } catch (e: any) {
            alert(ErrorRenderer.toDisplayFormat(e));
        }
    }

    async function handleLogout() {
        try {
            const logoutResponse = await logout();
            onLoggedOut();
            if (logoutResponse.logoutUrl) {
                window.location.href = logoutResponse.logoutUrl;
            } else {
                window.location.href = window.location.origin;
            }
        } catch (e: any) {
            if (e.status === 401) {
                onLoggedOut();
                return;
            }
            alert(ErrorRenderer.toDisplayFormat(e));
        }
    }

    return (
        <TopBarView
            isLoggedIn={isLoggedIn}
            initials={initials}
            onLogin={handleLogin}
            onLogout={handleLogout}
        />
    );
}
