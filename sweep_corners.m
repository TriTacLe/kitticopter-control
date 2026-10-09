% Runs the kitticopter model at the three drag corners and the gain corners.
% Build the model once with build_kitticopter, then run this.

a = 2.4322; k = 0.95; Vhover = 2.5; b0 = 0.10485;

fprintf('\n drag corners, Kp = 0.005\n');
for bscale = [0.9 1.0 1.1]
    b = b0*bscale;  A = a/b;  T = 1/b;  Kp = 0.005;
    report(bscale, 1.0, A, T, k, Kp);
end

fprintf('\n gain corners, b nominal\n');
b = b0;  A = a/b;  T = 1/b;
for g = [0.9 1.0 1.1]
    Kp = 0.005*g;
    report(1.0, g, A, T, k, Kp);
end

fprintf('\n worst case, b -10%% with the gain high\n');
b = b0*0.9;  A = a/b;  T = 1/b;  Kp = 0.005*1.22;
report(0.9, 1.22, A, T, k, Kp);

function report(bs, gs, A, T, k, Kp)
    zeta = 1/(2*sqrt(Kp*k*A*T));
    wn   = sqrt(Kp*k*A/T);
    OS   = 100*exp(-pi*zeta/sqrt(1-zeta^2));
    fprintf('  b %+4.0f%% gain %+4.0f%%: A %7.3f  T %7.3f  zeta %.3f  wn %.4f  OS %5.1f %%\n', ...
            (bs-1)*100, (gs-1)*100, A, T, zeta, wn, OS);
end
