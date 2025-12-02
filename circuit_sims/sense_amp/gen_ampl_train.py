

cur_time = 0;

def gen_pulse(out_file, edge_rate_ns, pulse_width_ns, pulse_height_mv, gap_ns=0):
    global cur_time

    out_file.write(f"{cur_time}n 0\n")
    cur_time += edge_rate_ns
    out_file.write(f"{cur_time}n {pulse_height_mv}m\n")
    cur_time += pulse_width_ns-edge_rate_ns
    out_file.write(f"{cur_time}n {pulse_height_mv}m\n")
    cur_time += edge_rate_ns
    out_file.write(f"{cur_time}n 0\n")
    cur_time += gap_ns

def advance_time(ns):
    global cur_time
    cur_time += ns

with open("ampl_train.pwl", 'w') as f:
    for pulse_height in range(2, 40, 2):
        gen_pulse(f, edge_rate_ns=50, pulse_width_ns=200, pulse_height_mv=pulse_height, gap_ns=300)

    advance_time(1000)

    for pulse_width in range(10, 300, 10):
        gen_pulse(f, edge_rate_ns=1, pulse_width_ns=pulse_width, pulse_height_mv=30, gap_ns=300)
        gen_pulse(f, edge_rate_ns=1, pulse_width_ns=pulse_width, pulse_height_mv=26, gap_ns=500)
