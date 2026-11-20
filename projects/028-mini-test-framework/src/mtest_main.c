/* Link this into a test binary to get a ready-made main(). Projects that
 * need their own main() can call mt_main() directly instead. */
#include "mtest.h"

int main(int argc, char **argv)
{
    return mt_main(argc, argv);
}
